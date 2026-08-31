# Portfolio Risk & Trading Monitor

A multi-agent portfolio risk assistant built on Microsoft's [Agent Framework](https://github.com/microsoft/agent-framework), using group chat orchestration and Azure AI Foundry.

You enter your holdings interactively; three specialist agents take turns analyzing them and hand off a final recommendation.

## Agents

| Agent | Role |
|---|---|
| **News Analyst** | Discusses market/news context and sentiment for the tickers you hold, based on its training knowledge (no live news feed). |
| **Risk Calculator** | Calls a `calculate_portfolio_risk` tool to compute position weights, the Herfindahl-Hirschman Index (HHI), and concentration flags. |
| **Advisor** | Synthesizes both agents' findings plus your risk tolerance and question into a final recommendation. |

## Orchestration

The three agents run under a `GroupChatBuilder` group chat orchestration (star topology): a central orchestrator routes each turn to a participant and stops the conversation once the Advisor has spoken. Turn order is deterministic — News Analyst → Risk Calculator → Advisor — via a `selection_func`, with `max_rounds` as a safety net against runaway loops.

## Prerequisites

- Python 3.10+
- An Azure AI Foundry project with a deployed chat model
- Azure CLI, logged in (`az login`) — the app authenticates via `AzureCliCredential`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
AZURE_AI_PROJECT_ENDPOINT=<your Azure AI Foundry project endpoint>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<your deployed model name>
```

## Usage — CLI

```bash
python portfolio_risk.py
```

You'll be prompted for:

1. **Holdings** — one per line, `TICKER QUANTITY PRICE` (e.g. `AAPL 50 190.32`), blank line to finish.
2. **Risk tolerance** — low / medium / high (defaults to medium).
3. **Question** — anything specific you want the Advisor to focus on (optional).

The app then runs the group chat and prints each agent's turn in order.

### Example session

```
Holding 1 (blank to finish): AAPL 50 190.32
Holding 2 (blank to finish): MSFT 10 420.00
Holding 3 (blank to finish): NVDA 8 118.50
Holding 4 (blank to finish):
Your risk tolerance (low / medium / high) [medium]: low
Anything specific you want the Advisor to focus on? (optional): Should I trim my Apple position?
```

## Usage — Web app

The same workflow is also available behind a React frontend backed by a FastAPI server, so you can enter holdings in a form instead of the terminal.

**1. Start the API** (from the project root, with the venv active and `.env` configured as above):

```bash
uvicorn api:app --reload --port 8000
```

**2. Start the frontend** (in a second terminal):

```bash
cd frontend
npm install   # first time only
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). Add holdings in the form, set your risk tolerance and optional question, and submit — the three agents' turns appear as cards on the right as the analysis completes.

The frontend calls the API at `http://localhost:8000` by default; override with a `VITE_API_URL` env var (e.g. in `frontend/.env`) if you run the API elsewhere.

## Project layout

- `portfolio_workflow.py` — shared agent definitions, the `calculate_portfolio_risk` tool, and the group chat orchestration. Used by both the CLI and the API.
- `portfolio_risk.py` — terminal entry point (prompts for input, prints the conversation).
- `api.py` — FastAPI server exposing `POST /api/analyze` for the frontend.
- `frontend/` — Vite + React UI.

## Notes

- This tool produces educational analysis, not licensed financial advice.
- The News Analyst has no live market/news access — verify anything time-sensitive against a real-time source before acting.
- The Risk Calculator's numbers are based only on the prices you enter, not live market data.
