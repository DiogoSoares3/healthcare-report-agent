import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from api.src.schemas import ChatRequest, ReportRequest, AgentResponse
from api.src.agents.orchestrator import get_orchestrator, SRAGAgentOrchestrator
from api.src.services.manage_plots import extract_plots_from_result
from api.src.db.minio_connection import upload_run_artifacts
from api.src.config import get_settings
from api.src.services.telemetry import set_trace_tags

router = APIRouter(prefix="/api/v1/agent", tags=["Agent"])
logger = logging.getLogger(__name__)

settings = get_settings()


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

    tags = {
        "genai.task": "executive_report",
        "genai.focus_area": request.focus_area if request.focus_area else "general",
    }
    set_trace_tags(tags)

    report_prompt = (
        "Generate a comprehensive **Executive Report** on the current **SRAG situation**.\n"
        "STRICTLY FOLLOW this structure and formatting rules:\n\n"
        "1. **KEY METRICS**: Calculate and present:\n"
        "   - Case Increase Rate (Growth %)\n"
        "   - Mortality Rate (CFR %)\n"
        "   - ICU Occupation Rate (%)\n"
        "   - Vaccination Rate for COVID-19 (%)\n"
        "   - Vaccination Rate for Influenza (Flu) (%)\n\n"
        "2. **VISUAL ANALYSIS** (Mandatory):\n"
        "   - You MUST generate two charts: 'trend_30d' and 'history_12m'.\n"
        "   - **IMPORTANT:** When embedding charts, use the EXACT filename returned by the tool (including .png):\n"
        "     `![Desc](/api/v1/plots/<exact_filename_from_tool_output>)`\n"
        "   - Do NOT use the local 'data/plots/' path in the Markdown link.\n\n"
        "3. **CONTEXTUAL ANALYSIS**:\n"
        "   Make web search to find relevant news (e.g., outbreaks, variants, public health events)\n"
        "   to provide context and support for the presented metrics, helping explain observed trends\n"
        "   and anomalies in the data.\n\n"
        "4. **CONCLUSION**: Brief executive summary. "
        "5. **OUTPUT FORMAT**:\n"
        "   - The report includes only the analytical sections defined above.\n"
        "   - The content is written in a neutral, report-style format.\n"
        "   - The document finishes at the conclusion section."
    )

    if request.focus_area:
        report_prompt += (
            f"\n\nAdditional Focus: Please specifically analyze {request.focus_area}."
        )

    try:
        result = await orchestrator.run(report_prompt)

        generated_plots = extract_plots_from_result(result)
        response_text = result.output

        upload_run_artifacts(response_text, generated_plots)

        return AgentResponse(
            response=response_text,
            plots=generated_plots,
            execution_time=time.time() - start_time,
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
