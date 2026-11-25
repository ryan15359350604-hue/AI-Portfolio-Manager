"""Income / expenses → annual net investment flows. Replace this adapter with your reviewed implementation."""

def run(payload: dict) -> dict:
    # payload: client, accounts, flows, market, policy, risk, macro, results, preferences
    return {"status": "not_connected", "module": "cashflows",
            "message": "Your team model has not been connected yet."}
