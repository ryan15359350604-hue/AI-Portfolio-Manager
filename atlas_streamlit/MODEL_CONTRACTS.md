# Model integration contracts

Every adapter receives one JSON-compatible snapshot with `client`, `accounts`, `flows`, `market`, `constraints`, `policy`, `risk`, `macro`, `results`, `preferences`, `reporting_basis`, `benchmarks`.

`results` contains outputs from prior module runs. Run the cashflow adapter before the required-return adapter, and the market-data / return-risk adapters before optimization. The current app exposes individual run buttons; it does not assume a universal automatic pipeline.

| Slot | Expected responsibility / suggested output |
|---|---|
| client_profile | Resolve age and gamma into a risky-asset constraint; report rule and meaning (fixed, maximum, reference). |
| cashflows | Reconcile income, expenses and contributions; annual nominal/real net investment schedule with sign and timing. |
| required_return | Consume schedule; solve return; include `display_value` such as `6.2%`, feasibility, basis and cash-flow timing. |
| market_data | Validate tickers; Yahoo prices / total-return assumptions, dates, frequency, currency, missing-data handling. |
| return_risk | Betas, forecasts, covariance and volatility with tickers and aligned frequency / annualization. |
| optimization | Net weights sum to one, including cash/borrowing; `weights: [{"ticker":"...","weight":0.5}, ...]`; optional `after_tax_return_display`, `volatility_display`. |
| tax | Realized gain tax from holdings / cost basis; distinguish taxable vs TFSA, room / withdrawals and income tax. |
| risk_metrics | VaR and ES with confidence, method, horizon and signed-loss convention / currency. |
| macro_shocks | Baseline and shocked factors with explicit units; calibrated asset transmission; baseline / shocked portfolio. |
| rebalancing | Apply review policy to the current simulated date; HOLD or proposed trades, tax, constraints, before/after measures. |
| benchmark | Same-period comparisons, wealth paths, risk and funding. |

API upload area supports an integration workflow, not automatic installation of arbitrary code on the server. Keep each adapter deterministic where possible and seed simulations. Include model/version/data timestamps in results for reproducibility.

## Example optimization output shape (schema only)

```json
{"status":"ok","weights":[{"ticker":"ASSET_A","weight":0.6},{"ticker":"CASH","weight":0.4}],"after_tax_return_display":"6.0%","volatility_display":"10.0%"}
```

These are documentation examples, never app model outputs.

## Macro import shape suggestion

```json
{"name":"Rate shock","frequency":"annual","units":{"rate_delta":"basis_points","inflation_delta":"percentage_points","output_delta":"percent"},"paths":[{"period":1,"rate_delta":75,"inflation_delta":1.0,"output_delta":-1.0}]}
```

The adapter owns interpretation / validation. Importing a macro file alone does not produce investment impacts.
