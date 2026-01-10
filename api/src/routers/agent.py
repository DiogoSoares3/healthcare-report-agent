import logging
import time
from fastapi import APIRouter, Depends, HTTPException

from api.src.schemas import ChatRequest, ReportRequest, AgentResponse
from api.src.agents.orchestrator import get_orchestrator, SRAGAgentOrchestrator

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: ChatRequest,
    orchestrator: SRAGAgentOrchestrator = Depends(get_orchestrator),
):
    """
    Free-form chat endpoint for follow-up questions.
    """
    start_time = time.time()
    try:
        response_text = await orchestrator.run(request.query)

        return AgentResponse(
            response=response_text, execution_time=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Chat execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report", response_model=AgentResponse)
async def generate_report(
    request: ReportRequest,
    orchestrator: SRAGAgentOrchestrator = Depends(get_orchestrator),
):
    """
    Generates the Executive Report as required by the GenAI Challenge.

    This endpoint injects a strict system prompt instruction to ensure the Agent:
    1. Calculates the 4 Key Metrics (Case Increase, Mortality, ICU, Vaccination).
    2. Generates the 2 Required Charts (30-day Trend, 12-Month History).
    3. Searches for News to contextually explain the data.
    """
    start_time = time.time()

    report_prompt = (
        "Generate a comprehensive Executive Report on the current SRAG situation for healthcare professionals.\n"
        "You MUST strictly follow this structure:\n\n"
        "1. **KEY METRICS**: Calculate and present:\n"
        "   - Case Increase Rate (Growth)\n"
        "   - Mortality Rate (CFR)\n"
        "   - ICU Occupation Rate\n"
        "   - Vaccination Rate\n\n"
        "2. **VISUAL ANALYSIS**: Generate and analyze two charts:\n"
        "   - Daily cases for the last 30 days ('trend_30d').\n"
        "   - Monthly cases for the last 12 months ('history_12m').\n\n"
        "3. **CONTEXTUAL ANALYSIS**: Use the search tool to find recent news (outbreaks, variants, vaccines) "
        "that explain the numbers found above.\n\n"
        "4. **CONCLUSION**: A brief summary of the severity."
    )

    if request.focus_area:
        report_prompt += (
            f"\n\nAdditional Focus: Please specifically analyze {request.focus_area}."
        )

    try:
        logger.info("Triggering Report Generation...")
        response_text = await orchestrator.run(report_prompt)

        return AgentResponse(
            response=response_text, execution_time=time.time() - start_time
        )
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate report.")
