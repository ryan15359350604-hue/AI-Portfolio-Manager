# ATLAS — Python + Streamlit

Navy / copper portfolio-manager framework for ECON9536. This is a runnable application, not a static mockup. The old Sites URL is unchanged.

## Run

Use Python 3.11 or 3.12. Unzip the folder, open a terminal inside it:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the localhost URL printed by Streamlit. Keep the terminal running.

## Enable real AI

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, enter your own OpenAI API key, choose a model your project can access, and set `ENABLE_AI = true`. The default configurable model is `gpt-4.1`. No key is bundled. ChatGPT login is not an API credential; this application uses a separate OpenAI API integration, not the running ChatGPT conversation. Do not upload API keys as code or enter them in the client chat.

The app calls the Responses API with a registered `run_model` tool. The AI sees the hypothetical client snapshot, qualitative preferences and model outputs after the user checks the sharing box. Source uploads, dependency files, data-file bytes and the API key are not placed in the prompt. No successful live API test has been performed without your credentials.

For a team demo, deploy privately before enabling a shared API key. A public app using your key can consume your API budget. Configure access and usage limits in your hosting/API accounts.

## Your models

All financial methods remain placeholders. No age-allocation mapping, DCF solver, beta forecast, tax rule, risk result or optimization is invented.

Modules in `models/` expose:

```python
def run(payload: dict) -> dict:
    return {"status": "ok", "your_result": ...}
```

Statuses: `ok`, `not_connected`, `infeasible`, `error`. Return JSON-serializable finite values; decimal returns and weights (0.05 = 5%). See `MODEL_CONTRACTS.md`.

The code uploader validates syntax and stages `.py` / `.ipynb` files in session memory. It does not install dependencies or execute visitor code. Download the integration bundle, review each module, replace the relevant `models/<slot>.py` adapter, add approved dependencies to requirements.txt, and restart / redeploy. Notebook code should be converted to functions first. Your adapter can call your existing functions; you do not need to rewrite them.

AI and UI buttons call the same reviewed adapters. Data downloads from Yahoo belong in `models/market_data.py`; yfinance is included as a dependency, but the downloader is not implemented because your team is supplying it. The AI shortlist must be reviewed and entered in the ticker field before data validation. Uploaded data is included in the downloaded integration bundle; adapters need an explicit reader to use it at runtime.

## Cash flows, accounts and policies

Gross salary is reference information, not automatically an investment contribution. The cash-flow module must avoid double-counting income and contributions, account for income tax separately from capital gains tax, and return an investable net cash-flow schedule. DCF reporting distinguishes real/nominal and after-tax returns. TFSA values are CAD even when base currency is USD; your model must handle FX and reconcile balances.

Review/rebalance frequency and triggers are simulation inputs only. This version does not run background jobs, trade, or connect a brokerage.

## Deployment

Streamlit Community Cloud: put the folder contents into your GitHub repository; deploy `app.py` from share.streamlit.io. Add secrets in the deployment settings (never commit secrets.toml). A Python server or Docker host also works. The previous static Sites host cannot run the Streamlit Python server. A persistent public URL has not been created for this version; deployment needs your chosen hosting account/repository.

## State & exports

Client inputs, uploads, model results and chat are per-session; no durable database is included. Export workspace JSON and staged integration ZIP before leaving. Workspace JSON excludes keys and chat history. Streamlit sessions do not share inputs. There is no import / full session restore in this version.

## Verify

```bash
python -m unittest discover -s tests -v
```

Tests cover adapter validation, missing-model behavior, signed weights, AI tool execution with a fake API client, and the Streamlit app through AppTest. They do not validate future financial models or live API / Yahoo connectivity.
