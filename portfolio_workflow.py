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

    # agent_framework validates tool arguments against a dynamic pydantic model but then
    # calls .model_dump() before invoking this function, which flattens nested Holding
    # instances back into plain dicts. Normalize defensively so both call styles work.
    holdings = [h if isinstance(h, Holding) else Holding.model_validate(h) for h in holdings]

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
# Agent + workflow construction
# ----------------------------------------------------------------------

NEWS_ANALYST_INSTRUCTIONS = """
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

RISK_CALCULATOR_INSTRUCTIONS = """
You are the Risk Calculator Agent on a portfolio risk & trading monitoring team.
You have a tool, calculate_portfolio_risk, that computes quantitative concentration
and diversification metrics (position weights, Herfindahl-Hirschman Index, effective
number of holdings) from a list of holdings (ticker, quantity, price).
Reconstruct the full holdings list from the conversation and call the tool exactly
once to get the numbers, then explain what they mean in plain English: which
positions dominate the portfolio, how diversified it is, and any concentration risk
worth flagging.
"""

ADVISOR_INSTRUCTIONS = """
You are the Advisor Agent on a portfolio risk & trading monitoring team, and you
speak last, after the News Analyst and Risk Calculator have both contributed.
Synthesize their findings together with the user's stated risk tolerance and
question into a short, actionable recommendation (e.g. hold, trim a concentrated
position, diversify into other sectors, monitor a specific catalyst).
Always end with a one-line disclaimer that this is educational analysis, not
licensed financial advice.
"""


def build_workflow():
    """Create the chat client, the three specialist agents, and the group chat workflow."""
    credential = AzureCliCredential()
    chat_client = FoundryChatClient(
        credential=credential,
        project_endpoint=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        model=os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME"),
    )

    news_analyst_agent = chat_client.as_agent(
        name="News_Analyst",
        description="Analyzes market and news context for the portfolio's holdings.",
        instructions=NEWS_ANALYST_INSTRUCTIONS,
    )

    risk_calculator_agent = chat_client.as_agent(
        name="Risk_Calculator",
        description="Computes quantitative concentration and diversification risk metrics.",
        instructions=RISK_CALCULATOR_INSTRUCTIONS,
        tools=calculate_portfolio_risk,
    )

    advisor_agent = chat_client.as_agent(
        name="Advisor",
        description="Synthesizes the other agents' findings into a final recommendation.",
        instructions=ADVISOR_INSTRUCTIONS,
    )

    # Group chat orchestration: a central orchestrator routes each turn to a
    # participant (star topology) based on select_next_speaker, and the chat ends once
    # advisor_has_spoken is true. max_rounds is a safety net against runaway loops.
    workflow = GroupChatBuilder(
        participants=[news_analyst_agent, risk_calculator_agent, advisor_agent],
        selection_func=select_next_speaker,
        termination_condition=advisor_has_spoken,
        max_rounds=len(SPEAKER_ORDER) + 1,
        output_from="all",
    ).build()

    return workflow


async def run_portfolio_analysis(
    holdings: list[Holding], risk_tolerance: str, question: str
) -> list[dict[str, str]]:
    """Run the group chat and return each turn as {"agent": name, "text": message}."""
    initial_message = build_initial_message(holdings, risk_tolerance, question)
    workflow = build_workflow()

    result = await workflow.run(initial_message)
    outputs = result.get_outputs()

    turns: list[dict[str, str]] = []
    for response in outputs:
        for msg in cast(list[Message], response.messages):
            name = msg.author_name or ("assistant" if msg.role == "assistant" else "user")
            turns.append({"agent": name, "text": msg.text})

    return turns
