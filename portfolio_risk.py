import asyncio

from portfolio_workflow import Holding, run_portfolio_analysis


# ----------------------------------------------------------------------
# User input
# ----------------------------------------------------------------------

def prompt_for_holdings() -> list[Holding]:
    print("Enter your portfolio holdings one at a time.")
    print("Format: TICKER QUANTITY PRICE   e.g. AAPL 50 190.32")
    print("Press Enter on a blank line when you're done.\n")

    holdings: list[Holding] = []
    while True:
        line = input(f"Holding {len(holdings) + 1} (blank to finish): ").strip()
        if not line:
            if holdings:
                break
            print("Please enter at least one holding before finishing.")
            continue

        parts = line.split()
        if len(parts) != 3:
            print("  Couldn't parse that. Use: TICKER QUANTITY PRICE")
            continue

        ticker, quantity_str, price_str = parts
        try:
            quantity = float(quantity_str)
            price = float(price_str)
        except ValueError:
            print("  Quantity and price must be numbers.")
            continue

        if quantity <= 0 or price <= 0:
            print("  Quantity and price must be positive numbers.")
            continue

        holdings.append(Holding(ticker=ticker.upper(), quantity=quantity, price=price))

    return holdings


def prompt_for_risk_tolerance() -> str:
    tolerance = input("Your risk tolerance (low / medium / high) [medium]: ").strip()
    return tolerance or "medium"


def prompt_for_question() -> str:
    question = input("Anything specific you want the Advisor to focus on? (optional): ").strip()
    return question or "Give me a general risk assessment and recommendation for this portfolio."


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("Portfolio Risk & Trading Monitor")
    print("=" * 60)
    print()

    holdings = prompt_for_holdings()
    risk_tolerance = prompt_for_risk_tolerance()
    question = prompt_for_question()

    print("\nRunning the group chat orchestration...\n")

    turns = await run_portfolio_analysis(holdings, risk_tolerance, question)

    for i, turn in enumerate(turns, start=1):
        print(f"{'-' * 60}\n{i:02d} [{turn['agent']}]\n{turn['text']}")


if __name__ == "__main__":
    asyncio.run(main())
