import asyncio
import os
from typing import Annotated, cast

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Add references
from agent_framework import Message
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from azure.identity import AzureCliCredential


load_dotenv()


# ----------------------------------------------------------------------
# Risk Calculator tool
# ----------------------------------------------------------------------

class Holding(BaseModel):
    ticker: Annotated[str, Field(description="Stock ticker symbol, e.g. AAPL")]
    quantity: Annotated[float, Field(description="Number of shares held")]
    price: Annotated[float, Field(description="Current price per share in USD")]


def calculate_portfolio_risk(
    holdings: Annotated[
        list[Holding],
        Field(description="The full list of portfolio holdings reported by the user."),
    ],
) -> str:
    """Compute quantitative concentration and diversification risk metrics for a portfolio.

    Calculates each position's market value and weight, the Herfindahl-Hirschman Index (HHI)
    of concentration, the effective number of independent positions (1 / HHI), and flags any
    single position that exceeds a 25% concentration threshold. Call this once, after you know
    the full list of holdings from the conversation.
    """
    if not holdings:
        return "No holdings provided; cannot compute risk metrics."

    values = [h.quantity * h.price for h in holdings]
    total_value = sum(values)
    if total_value <= 0:
        return "Total portfolio value is zero or negative; cannot compute risk metrics."

    weights = [v / total_value for v in values]
    hhi = sum(w * w for w in weights)
    effective_holdings = 1 / hhi if hhi > 0 else 0.0

    if hhi < 0.15:
        concentration_level = "Low"
    elif hhi < 0.25:
        concentration_level = "Moderate"
    else:
        concentration_level = "High"

    rows = sorted(zip(holdings, values, weights), key=lambda row: row[2], reverse=True)

    lines = ["Portfolio risk metrics:", f"Total market value: ${total_value:,.2f}", ""]
    for holding, value, weight in rows:
        flag = "  <-- concentrated position (>25%)" if weight > 0.25 else ""
        lines.append(
            f"  {holding.ticker}: {holding.quantity:g} sh @ ${holding.price:,.2f} "
            f"= ${value:,.2f} ({weight:.1%}){flag}"
        )

    lines.append("")
    lines.append(f"Herfindahl-Hirschman Index (HHI): {hhi:.3f}")
    lines.append(f"Effective number of independent positions: {effective_holdings:.1f}")
    lines.append(f"Concentration level: {concentration_level}")
    lines.append(f"Number of holdings: {len(holdings)}")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# Group chat orchestration
# ----------------------------------------------------------------------

SPEAKER_ORDER = ["News_Analyst", "Risk_Calculator", "Advisor"]


def select_next_speaker(state: GroupChatState) -> str:
    """Deterministically route turns: News Analyst -> Risk Calculator -> Advisor."""
    return SPEAKER_ORDER[state.current_round % len(SPEAKER_ORDER)]


def advisor_has_spoken(conversation: list[Message]) -> bool:
    """Stop the group chat once the Advisor has delivered its recommendation."""
    return any(msg.author_name == "Advisor" for msg in conversation)


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


def build_initial_message(holdings: list[Holding], risk_tolerance: str, question: str) -> str:
    holdings_lines = "\n".join(
        f"- {h.ticker}: {h.quantity:g} shares @ ${h.price:,.2f}" for h in holdings
    )
    return (
        "Analyze the following investment portfolio.\n\n"
        f"Holdings:\n{holdings_lines}\n\n"
        f"Stated risk tolerance: {risk_tolerance}\n"
        f"User's question: {question}"
    )


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
    initial_message = build_initial_message(holdings, risk_tolerance, question)

    # Agent instructions
    news_analyst_instructions = """
    You are the News Analyst Agent on a portfolio risk & trading monitoring team.
    Given the user's portfolio holdings and stated concerns, discuss the market and
    news context relevant to each ticker held: recent sector trends, competitive or
    macro catalysts, and general sentiment, drawing on your training knowledge.
    Be explicit that you do not have live, real-time news access and your knowledge
    has a cutoff, so anything published after that date -- and same-day price moves --
    should be verified by the user against a live source before acting.
    Keep your analysis focused on the tickers in the portfolio. Do not invent specific
    headlines, prices, or dates you are not confident about.
    """

    risk_calculator_instructions = """
    You are the Risk Calculator Agent on a portfolio risk & trading monitoring team.
    You have a tool, calculate_portfolio_risk, that computes quantitative concentration
    and diversification metrics (position weights, Herfindahl-Hirschman Index, effective
    number of holdings) from a list of holdings (ticker, quantity, price).
    Reconstruct the full holdings list from the conversation and call the tool exactly
    once to get the numbers, then explain what they mean in plain English: which
    positions dominate the portfolio, how diversified it is, and any concentration risk
    worth flagging.
    """

    advisor_instructions = """
    You are the Advisor Agent on a portfolio risk & trading monitoring team, and you
    speak last, after the News Analyst and Risk Calculator have both contributed.
    Synthesize their findings together with the user's stated risk tolerance and
    question into a short, actionable recommendation (e.g. hold, trim a concentrated
    position, diversify into other sectors, monitor a specific catalyst).
    Always end with a one-line disclaimer that this is educational analysis, not
    licensed financial advice.
    """

    # Create the chat client
    credential = AzureCliCredential()
    chat_client = FoundryChatClient(
        credential=credential,
        project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        model=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
    )

    # Create agents
    news_analyst_agent = chat_client.as_agent(
        name="News_Analyst",
        description="Analyzes market and news context for the portfolio's holdings.",
        instructions=news_analyst_instructions,
    )

    risk_calculator_agent = chat_client.as_agent(
        name="Risk_Calculator",
        description="Computes quantitative concentration and diversification risk metrics.",
        instructions=risk_calculator_instructions,
        tools=calculate_portfolio_risk,
    )

    advisor_agent = chat_client.as_agent(
        name="Advisor",
        description="Synthesizes the other agents' findings into a final recommendation.",
        instructions=advisor_instructions,
    )

    # Build group chat orchestration: a central orchestrator routes each turn to a
    # participant (star topology) based on select_next_speaker, and the chat ends once
    # advisor_has_spoken is true. max_rounds is a safety net against runaway loops.
    workflow = GroupChatBuilder(
        participants=[news_analyst_agent, risk_calculator_agent, advisor_agent],
        selection_func=select_next_speaker,
        termination_condition=advisor_has_spoken,
        max_rounds=len(SPEAKER_ORDER) + 1,
        output_from="all",
    ).build()

    print("\nRunning the group chat orchestration...\n")

    # Run and collect outputs
    result = await workflow.run(initial_message)
    outputs = result.get_outputs()

    # Display outputs
    i = 1
    for response in outputs:
        for msg in cast(list[Message], response.messages):
            name = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
            print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")
            i += 1


if __name__ == "__main__":
    asyncio.run(main())
