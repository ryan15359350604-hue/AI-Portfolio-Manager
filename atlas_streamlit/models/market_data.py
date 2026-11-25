"""Yahoo or uploaded data → return history. Replace this adapter with your reviewed implementation."""

def run(payload: dict) -> dict:
    # payload: client, accounts, flows, market, policy, risk, macro, results, preferences
    return {"status": "not_connected", "module": "market_data",
            "message": "Your team model has not been connected yet."}
