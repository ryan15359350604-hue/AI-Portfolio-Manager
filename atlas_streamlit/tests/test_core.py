import unittest
from types import SimpleNamespace as NS
from core.engine import inspect_code, run_model, portfolio_table
from core.ai import respond

class CoreTests(unittest.TestCase):
    def test_upload_inspection_does_not_execute(self):
        r=inspect_code('a.py',b'raise RuntimeError("never execute")\ndef run(payload): return {}')
        self.assertEqual(r['functions'],['run'])
    def test_missing_model_explicit(self):
        self.assertEqual(run_model('optimization',{})['status'],'not_connected')
        with self.assertRaises(ValueError):run_model('../other',{})
    def test_signed_weights_and_invalid_total(self):
        self.assertEqual(len(portfolio_table({'weights':[{'ticker':'A','weight':1.2},{'ticker':'CASH','weight':-.2}]})),2)
        with self.assertRaises(ValueError):portfolio_table({'weights':[{'ticker':'A','weight':2}]})
    def test_ai_tool_handoff(self):
        class Responses:
            def __init__(self):self.calls=[]
            def create(self,**kwargs):
                self.calls.append(kwargs)
                if len(self.calls)==1:return NS(output=[NS(type='function_call',name='run_model',call_id='c1',arguments='{"module":"optimization"}')],output_text='')
                self.payload=kwargs['input'][-1]
                return NS(output=[],output_text='Optimization is not connected.')
        api=NS(responses=Responses())
        answer,traces=respond('unused','model',[{'role':'user','content':'Optimize'}],{},client=api)
        self.assertIn('not connected',answer)
        self.assertEqual(traces[0]['result']['status'],'not_connected')
        self.assertFalse(api.responses.calls[0]['store'])
    def test_app_initial_render(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'app.py')).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.tabs),7)
        self.assertTrue(app.chat_input[0].disabled)
        # Model button must surface missing adapter rather than fabricated success.
        next(x for x in app.button if x.label=='Optimize portfolio').click().run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.session_state['results']['optimization']['status'],'not_connected')
        next(x for x in app.number_input if x.label=='Age').set_value(50).run()
        self.assertEqual(app.session_state['results'],{})
        next(x for x in app.selectbox if x.label=='Scheduled rebalancing').set_value('Annual').run()
        self.assertEqual(len(app.exception),0)

if __name__=='__main__':unittest.main()
