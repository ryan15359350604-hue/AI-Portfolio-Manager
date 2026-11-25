"""Explicit adapter contracts. Missing models fail closed; there are no invented outputs."""
import ast
import hashlib
import importlib
import json
from pathlib import Path

MODULES = {
 'client_profile': 'Age / risk preferences → constraints',
 'cashflows': 'Income / expenses → annual net investment flows',
 'required_return': 'Cash-flow discounting → required return',
 'market_data': 'Yahoo or uploaded data → return history',
 'return_risk': 'Beta / forecasts / covariance',
 'optimization': 'Constraints and forecasts → portfolio weights',
 'tax': 'TFSA / taxable cost basis → tax calculations',
 'risk_metrics': 'VaR / ES',
 'macro_shocks': 'Macro factors → asset / portfolio shocks',
 'rebalancing': 'Policy and holdings → hold / rebalance decision',
 'benchmark': 'Comparable performance results',
}

def inspect_code(name, content):
    if len(content) > 2_000_000:
        raise ValueError('Code exceeds the 2 MB module limit.')
    source = content.decode('utf-8')
    if name.endswith('.ipynb'):
        notebook = json.loads(source)
        source = '\n'.join(''.join(c.get('source', [])) for c in notebook.get('cells', []) if c.get('cell_type') == 'code')
    try:
        tree = ast.parse(source)
        functions = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        syntax = 'Valid Python syntax'
    except SyntaxError as exc:
        functions = []
        syntax = f'Syntax issue at line {exc.lineno}: {exc.msg}; notebook magics need conversion.'
    return {'sha256': hashlib.sha256(content).hexdigest(), 'functions': functions, 'syntax': syntax, 'source': source}

def run_model(module, payload):
    if module not in MODULES:
        raise ValueError('Unknown model module')
    adapter = importlib.import_module(f'models.{module}')
    result = adapter.run(payload)
    if not isinstance(result, dict) or result.get('status') not in {'ok', 'not_connected', 'infeasible', 'error'}:
        raise ValueError('Model must return a dict with status ok/not_connected/infeasible/error.')
    json.dumps(result, allow_nan=False)
    return result

def portfolio_table(result):
    """Validate before displaying weights; support short positions without a misleading pie."""
    import pandas as pd
    df = pd.DataFrame(result.get('weights', []))
    if df.empty:
        return df
    if not {'ticker', 'weight'}.issubset(df.columns):
        raise ValueError('weights requires ticker and weight columns')
    df['weight'] = pd.to_numeric(df['weight'], errors='raise')
    import math
    if any(not math.isfinite(x) for x in df.weight):
        raise ValueError('Weights must be finite')
    if abs(df.weight.sum() - 1) > 0.001:
        raise ValueError('Net portfolio weights must sum to 1, including cash / borrowing.')
    return df
