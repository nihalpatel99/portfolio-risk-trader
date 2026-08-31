from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from portfolio_workflow import Holding, run_portfolio_analysis

app = FastAPI(title="Portfolio Risk & Trading Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    holdings: list[Holding] = Field(min_length=1)
    risk_tolerance: str = "medium"
    question: str = "Give me a general risk assessment and recommendation for this portfolio."


class Turn(BaseModel):
    agent: str
    text: str


class AnalyzeResponse(BaseModel):
    turns: list[Turn]


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        turns = await run_portfolio_analysis(
            request.holdings, request.risk_tolerance, request.question
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnalyzeResponse(turns=turns)
