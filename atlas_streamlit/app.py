import io
import hashlib
import json
import os
from datetime import datetime, timezone
from zipfile import ZipFile
import pandas as pd
import plotly.express as px
import streamlit as st
from core.engine import MODULES, inspect_code, run_model, portfolio_table
from core.ai import respond

st.set_page_config(page_title='ATLAS · Portfolio Intelligence', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp{background:#f6f5f1} .block-container{padding-top:2rem;max-width:1700px} h1,h2,h3{color:#152a43} h1{font-family:Georgia,serif;font-weight:500;letter-spacing:-1px} [data-testid="stSidebar"]{background:#14243c} [data-testid="stSidebar"] *{color:#f6f5f1} .brand{background:#14243c;color:white;padding:22px 28px;border-radius:8px;font:25px Georgia;margin-bottom:25px}.brand span{color:#cf9369}.brand small{font:12px Arial;color:#c2cede;margin-left:20px}.stButton>button[kind="primary"]{background:#b87347;border:0}.stMetric{background:white;border:1px solid #dee2e7;border-radius:8px;padding:16px} [data-testid="stTabs"]{margin-top:15px} div[data-testid="stVerticalBlockBorderWrapper"]{background:#fff} .eyebrow{font-size:11px;letter-spacing:2px;color:#7b8899}.muted{color:#748195} .stDownloadButton button{width:100%}
</style>''', unsafe_allow_html=True)
for k,v in {'messages':[], 'results':{}, 'uploads':{}, 'logs':[], 'shortlist':[], 'data_files':{}, 'preferences':''}.items():
    if k not in st.session_state: st.session_state[k]=v

def secret(name, default=''):
    try: return st.secrets.get(name, os.getenv(name,default))
    except (FileNotFoundError, KeyError): return os.getenv(name,default)

def record(module, payload):
    try:
        result=run_model(module,payload)
    except Exception as exc:
        result={'status':'error','message':str(exc)}
    st.session_state.results[module]=result
    st.session_state.logs.append({'time':datetime.now(timezone.utc).isoformat(),'module':module,'result':result})
    if result['status']=='ok': st.success(f'{module}: completed')
    else: st.warning(result.get('message', result['status']))
    return result

def show_result(module):
    r=st.session_state.results.get(module)
    if r:
        with st.expander(f'{module} · {r["status"]}'):st.json(r)

st.markdown('<div class="brand">ATLAS <span>/</span> Portfolio Intelligence <small>ECON 9536 · Research workspace</small></div>',unsafe_allow_html=True)
with st.sidebar:
    st.header('Workspace')
    st.caption('Python + Streamlit')
    st.info('Framework ready. Financial models await your team’s code.')
    st.markdown('**Workflow**\n\nClient needs → Cash flows → Required return → AI shortlist → Forecasts → Optimize → Monitor')
    st.divider()
    st.caption('AI settings')
    enabled=secret('ENABLE_AI',False)
    enabled=str(enabled).lower() in {'true','1','yes'}
    api_key=secret('OPENAI_API_KEY')
    model=secret('OPENAI_MODEL','gpt-4.1')
    st.write('● Connected' if api_key and enabled else '○ Not connected')
    st.caption(f'Model: {model}')
    st.caption('Configure OPENAI_API_KEY and ENABLE_AI in server Secrets. Do not paste keys into chat or source uploads.')

st.markdown('<div class="eyebrow">CLIENT WORKSPACE / NEW PLAN</div>',unsafe_allow_html=True)
st.title('A portfolio built around your client.')
st.caption('Define the goals. Connect your models. Review the decisions.')
left,right=st.columns([3.4,1.25],gap='large')
with left:
    tabs=st.tabs(['Client & accounts','Cash-flow plan','Models & data','Portfolio','Risk & macro','Rebalance','Compare'])
    with tabs[0]:
        with st.container(border=True):
            st.subheader('01 / Client profile')
            a,b,c=st.columns(3)
            name=a.text_input('Client / plan name','Education fund')
            age=b.number_input('Age',18,100,42)
            kids=c.number_input('Number of children',0,20,2)
            a,b,c=st.columns(3)
            wealth=a.number_input('Initial investable wealth',min_value=0.0,value=250000.0,step=1000.0)
            income=b.number_input('Annual gross income',min_value=0.0,value=110000.0,step=1000.0)
            horizon=c.number_input('Investment horizon · years',1,70,18)
            a,b=st.columns(2)
            gamma=a.slider('Risk aversion · γ',0.5,10.0,3.0,0.5,help='Higher means more risk averse. Your model defines the mapping to asset weights.')
            esg=b.slider('ESG preference strength',0,100,60)
            a,b=st.columns(2)
            retire=a.number_input('Retirement age',18,100,65)
            currency=b.selectbox('Base currency',['CAD','USD'])
        with st.container(border=True):
            st.subheader('Accounts & tax')
            a,b=st.columns(2)
            tfsa=a.toggle('Client has a TFSA',True)
            tax=b.slider('Effective realized capital gains tax · %',0.0,60.0,25.0,0.5)
            a,b,c=st.columns(3)
            balance=a.number_input('TFSA balance · CAD',min_value=0.0,value=35000.0 if tfsa else 0.0,disabled=not tfsa)
            room=b.number_input('Available TFSA contribution room · CAD',min_value=0.0,value=12000.0 if tfsa else 0.0,disabled=not tfsa)
            taxable=c.number_input('Taxable account balance',min_value=0.0,value=215000.0,step=1000.0)
            if currency=='CAD' and abs((balance if tfsa else 0)+taxable-wealth)>0.01:
                st.warning('Account balances do not match initial wealth. Reconcile before running financial models.')
            st.caption('Tax rate is a model assumption. TFSA amounts remain CAD; cross-currency conversion and account eligibility belong in your tax model.')
            holdings=st.data_editor(pd.DataFrame(columns=['ticker','account','quantity','price','cost_basis_total']),num_rows='dynamic',key='holdings',width='stretch')
            st.caption('Holdings and cost basis are required for meaningful rebalancing and realized-gains calculations.')
    with tabs[1]:
        st.subheader('02 / Income, spending & financial goals')
        st.caption('Positive amounts; direction determines the cash-flow sign. Income and expenses must not also be duplicated as contributions / withdrawals.')
        flows=st.data_editor(pd.DataFrame([
            {'purpose':'Salary','type':'Income','amount':110000.0,'start_year':1,'end_year':18,'frequency':'Annual','basis':'Today’s money'},
            {'purpose':'Living expenses','type':'Expense','amount':70000.0,'start_year':1,'end_year':18,'frequency':'Annual','basis':'Today’s money'},
            {'purpose':'Education','type':'Withdrawal','amount':150000.0,'start_year':12,'end_year':12,'frequency':'Once','basis':'Today’s money'},
        ]),num_rows='dynamic',key='flows',width='stretch',column_config={
            'type':st.column_config.SelectboxColumn(options=['Income','Expense','Contribution','Withdrawal']),
            'frequency':st.column_config.SelectboxColumn(options=['Annual','Once']),
            'basis':st.column_config.SelectboxColumn(options=['Today’s money','Future nominal']),
            'amount':st.column_config.NumberColumn(min_value=0),
            'start_year':st.column_config.NumberColumn(min_value=1), 'end_year':st.column_config.NumberColumn(min_value=1)})
        a,b=st.columns(2)
        inheritance=a.number_input('Terminal inheritance target',min_value=0.0,value=0.0)
        basis=b.selectbox('Required-return reporting basis',['Nominal after tax','Real after tax'])
        st.info('Your cash-flow adapter must reconcile gross income, income tax, spending and investable savings. The required-return solver will then use the resulting net schedule.')
    with tabs[2]:
        st.subheader('03 / Models & code')
        st.caption('Upload your team’s Python modules or notebooks here. Uploads are staged for integration; they do not execute automatically.')
        module=st.selectbox('Model slot',list(MODULES),format_func=lambda x:f'{x} — {MODULES[x]}')
        code=st.file_uploader('Upload code · .py / .ipynb',type=['py','ipynb'],key='code_upload')
        if code:
            try:
                inspected=inspect_code(code.name,code.getvalue())
                st.write(inspected['syntax'])
                st.caption('Top-level functions: '+(', '.join(inspected['functions']) or 'None detected'))
                st.code(inspected['source'][:15000],language='python')
                if st.button('Stage this version',type='primary'):
                    st.session_state.uploads[module]={'filename':code.name,'bytes':code.getvalue(),'sha256':inspected['sha256']}
                    st.success('Version staged. Download the integration bundle below; connect reviewed code to models/'+module+'.py and redeploy.')
            except (ValueError,UnicodeError,KeyError) as exc:st.error(str(exc))
        st.caption('Expected adapter contract')
        st.code('def run(payload: dict) -> dict:\n    # Use client, accounts, flows, market, policy, risk, macro, results\n    return {"status": "ok", "your_output": ...}',language='python')
        st.markdown('**Staged versions**')
        st.dataframe([{'slot':k,'filename':v['filename'],'sha256':v['sha256'][:12],'state':'Staged — not installed'} for k,v in st.session_state.uploads.items()],width='stretch')
        data=st.file_uploader('Model data / dependencies',type=['csv','xlsx','json','txt'],accept_multiple_files=True)
        for f in data:
            st.session_state.data_files[f.name]=f.getvalue()
        st.caption('Data files are staged for your adapters; no dependency installation or arbitrary source execution occurs from a visitor upload.')
        with st.expander('Market assumptions'):
            a,b,c=st.columns(3)
            rf=a.number_input('Risk-free rate · %',value=4.0,step=0.1)
            inflation=b.number_input('Expected inflation · %',value=2.5,step=0.1)
            mrp=c.number_input('Market risk premium · %',value=5.0,step=0.1)
            proxy=st.text_input('Risk-free proxy','3-year US Treasury')
            st.caption('Use a currency-consistent risk-free proxy or explicitly model FX. Market data is not live until your data adapter is connected.')
        tickers=st.text_input('Reviewed asset tickers · comma separated','',help='AI proposes tickers in chat; review and paste them here before market-data validation.')
    with tabs[3]:
        st.subheader('04 / Portfolio studio')
        a,b,c=st.columns(3)
        short=a.toggle('Allow short selling',True)
        gross=b.slider('Gross exposure cap · %',100,300,150,10)
        max_weight=c.slider('Maximum asset weight · %',5,100,30,5)
        mapping=st.selectbox('Age-model risky proportion used as',['To be specified','Fixed weight','Upper bound','Reference only'])
        st.caption('Allocation and funding results remain blank until your financial models are connected.')
    with tabs[4]:
        st.subheader('05 / Risk & macro scenarios')
        a,b,c=st.columns(3)
        confidence=a.selectbox('VaR / ES confidence',[0.95,0.975,0.99],format_func=lambda v:f'{v:.1%}')
        days=b.number_input('Risk horizon · trading days',1,252,21)
        method=c.selectbox('Risk method',['Historical','Parametric','Monte Carlo'])
        macro_file=st.file_uploader('Import macro model scenario · JSON',type='json',key='macro_file')
        macro={}
        if macro_file:
            try:
                macro=json.load(macro_file)
                if not isinstance(macro,dict):raise ValueError('Scenario must be a JSON object.')
                st.json(macro)
            except (ValueError,TypeError) as exc:st.error(str(exc));macro={}
        a,b,c=st.columns(3)
        dr=a.number_input('Interest-rate shock · basis points',value=75.0)
        dpi=b.number_input('Inflation shock · percentage points',value=1.0)
        dy=c.number_input('Output shock · %',value=-1.0)
        st.caption('Macro-to-asset transmission is a separate adapter. These inputs do not automatically imply asset return changes.')
    with tabs[5]:
        st.subheader('06 / Monitoring & rebalancing policy')
        a,b,c=st.columns(3)
        review=a.selectbox('Review frequency',['Monthly','Quarterly','Semiannual','Annual'])
        frequency=b.selectbox('Scheduled rebalancing',['Monthly','Quarterly','Semiannual','Annual','Trigger only'],index=1)
        policy_type=c.selectbox('Policy type',['Hybrid','Scheduled','Trigger-based'])
        a,b=st.columns(2)
        drift=a.slider('Weight drift trigger · percentage points',1,20,5)
        shock_review=b.toggle('Review after a macro shock',True)
        st.caption('A review can conclude HOLD. Policy controls are simulation inputs; no background scheduler or brokerage execution is enabled.')
    with tabs[6]:
        st.subheader('07 / Benchmark comparison')
        benchmarks=st.multiselect('Benchmarks',['S&P 500','Markowitz'],default=['S&P 500','Markowitz'])
        st.caption('Use the same data period, currency, cash-flow convention and comparable tax assumptions. No guaranteed outperformance.')

# Create one snapshot after all input controls have been evaluated.
def rows(df):
    return json.loads(df.to_json(orient='records'))
workspace={'schema_version':'1.0','client':{'name':name,'age':age,'children':kids,'wealth':wealth,'annual_gross_income':income,'horizon_years':horizon,'retirement_age':retire,'risk_aversion':gamma,'esg_strength':esg,'base_currency':currency,'inheritance_target':inheritance},'accounts':{'has_tfsa':tfsa,'tfsa_balance_cad':balance if tfsa else 0,'tfsa_room_cad':room if tfsa else 0,'taxable_balance':taxable,'effective_capital_gains_tax':tax/100,'holdings':rows(holdings)},'flows':rows(flows),'market':{'risk_free_rate':rf/100,'inflation':inflation/100,'market_risk_premium':mrp/100,'risk_free_proxy':proxy,'reviewed_tickers':[x.strip().upper() for x in tickers.split(',') if x.strip()]},'constraints':{'allow_short':short,'gross_exposure_cap':gross/100,'max_asset_weight':max_weight/100,'age_weight_rule':mapping},'policy':{'review_frequency':review,'rebalance_frequency':frequency,'type':policy_type,'drift_pp':drift,'shock_review':shock_review},'risk':{'confidence':confidence,'horizon_trading_days':days,'method':method},'macro':macro or {'rate_delta_bps':dr,'inflation_delta_pp':dpi,'output_delta_pct':dy},'reporting_basis':basis,'benchmarks':benchmarks,'preferences':st.session_state.preferences,'results':dict(st.session_state.results)}
# Invalidate displayed calculations when their input snapshot changes.
input_snapshot = {k:v for k,v in workspace.items() if k != 'results'}
fingerprint = hashlib.sha256(json.dumps(input_snapshot,sort_keys=True,allow_nan=False).encode()).hexdigest()
if st.session_state.get('input_fingerprint') not in (None, fingerprint):
    st.session_state.results = {}
    workspace['results'] = {}
    st.session_state.messages = []
st.session_state.input_fingerprint = fingerprint
with left:
    with tabs[1]:
        a,b=st.columns(2)
        if a.button('Build cash-flow schedule'):record('cashflows',workspace)
        if b.button('Find required return'):record('required_return',workspace)
        show_result('cashflows');show_result('required_return')
    with tabs[2]:
        a,b=st.columns(2)
        if a.button('Run market data model'):record('market_data',workspace)
        if b.button('Run beta & return model'):record('return_risk',workspace)
        show_result('market_data');show_result('return_risk')
    with tabs[3]:
        a,b=st.columns(2)
        if a.button('Run client-profile model'):record('client_profile',workspace)
        if b.button('Optimize portfolio',type='primary'):record('optimization',workspace)
        result=st.session_state.results.get('optimization',{})
        a,b,c=st.columns(3)
        a.metric('Required return',st.session_state.results.get('required_return',{}).get('display_value','—'))
        b.metric('Expected after-tax return',result.get('after_tax_return_display','—'))
        c.metric('Portfolio volatility',result.get('volatility_display','—'))
        if result.get('status')=='ok':
            try:
                weights=portfolio_table(result)
                if not weights.empty:
                    if (weights.weight<0).any():fig=px.bar(weights,x='ticker',y='weight',title='Long / short allocation')
                    else:fig=px.pie(weights,names='ticker',values='weight',hole=0.65,title='Portfolio allocation')
                    fig.update_layout(colorway=['#18324d','#7897b5','#bc784d','#cbd0d6'])
                    st.plotly_chart(fig,width='stretch');st.dataframe(weights,width='stretch')
            except ValueError as exc:st.error(str(exc))
        else:st.info('Portfolio charts will display connected model output. No illustrative weights are used.')
        if st.button('Evaluate taxes'):record('tax',workspace)
        show_result('optimization');show_result('tax')
    with tabs[4]:
        a,b=st.columns(2)
        if a.button('Calculate VaR & ES'):record('risk_metrics',workspace)
        if b.button('Simulate macro shock'):record('macro_shocks',workspace)
        show_result('risk_metrics');show_result('macro_shocks')
    with tabs[5]:
        if st.button('Evaluate hold vs rebalance',type='primary'):record('rebalancing',workspace)
        show_result('rebalancing')
    with tabs[6]:
        if st.button('Run benchmark comparison'):record('benchmark',workspace)
        show_result('benchmark')
        if st.session_state.logs:st.dataframe([{'time':x['time'],'module':x['module'],'status':x['result']['status']} for x in st.session_state.logs],width='stretch')
    st.divider()
    a,b=st.columns(2)
    # Export full current result state, without keys or source code.
    workspace['results']=dict(st.session_state.results)
    a.download_button('Export workspace JSON',json.dumps(workspace,indent=2,allow_nan=False),'atlas_workspace.json','application/json')
    buffer=io.BytesIO()
    with ZipFile(buffer,'w') as z:
        for slot,item in st.session_state.uploads.items():
            z.writestr(f'{slot}/{os.path.basename(item["filename"])}',item['bytes'])
        for filename,content in st.session_state.data_files.items():z.writestr('data/'+os.path.basename(filename),content)
        z.writestr('workspace.json',json.dumps(workspace,indent=2,allow_nan=False))
    b.download_button('Download staged integration bundle',buffer.getvalue(),'atlas_integration.zip','application/zip')
    st.caption('Uploads and chat belong to this session. Download a bundle before closing; model source is never sent to the AI automatically.')

with right:
    with st.container(border=True):
        st.subheader('✧ AI investment manager')
        st.caption('Qualitative needs → asset shortlist → registered model calls')
        if not api_key or not enabled:
            st.warning('AI not connected. Configure the server API key and ENABLE_AI=true in Secrets.')
        with st.expander('Client preferences · shared with AI'):
            preferences=st.text_area('Restrictions, priorities & goals',key='preferences')
            workspace['preferences']=preferences
        with st.container(height=510):
            if not st.session_state.messages:st.caption('Describe the client’s qualitative needs. Once connected, the AI can propose tickers and call your installed Python model adapters.')
            for msg in st.session_state.messages:
                with st.chat_message(msg['role']):st.markdown(msg['content'])
        share=st.checkbox('Send this hypothetical client workspace and model results to OpenAI when I send a message',value=False)
        prompt=st.chat_input('Discuss preferences or ask to run a model',disabled=not(api_key and enabled and share))
        if prompt:
            st.session_state.messages.append({'role':'user','content':prompt})
            try:
                with st.spinner('AI is reviewing the workspace…'):
                    reply,traces=respond(api_key,model,st.session_state.messages,workspace)
                st.session_state.messages.append({'role':'assistant','content':reply})
                for trace in traces:
                    st.session_state.results[trace['module']]=trace['result']
                    st.session_state.logs.append({'time':datetime.now(timezone.utc).isoformat(),**trace})
                st.rerun()
            except Exception:
                st.error('AI request failed. Check the API key, model access, network and billing in your server configuration. No response was fabricated.')
        if st.button('Clear chat'):
            st.session_state.messages=[];st.rerun()
        st.caption('AI proposes and explains. Your Python models calculate and validate. Academic simulation; no live trading.')
