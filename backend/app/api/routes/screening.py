from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.screening import ScreeningResponse, OfficerAction
from app.schemas.audit import OfficerAdjudicationRequest
from app.schemas.document import ValidatedInputDocument
from app.orchestration.workflow import get_pipeline, ScreeningPipelineOrchestrator
from app.database.repositories import ScreeningRepository
from app.core.security import generate_screening_id
from app.core.logging import get_logger

router = APIRouter(prefix="/screening", tags=["Core Screening Pipeline"])
logger = get_logger("screening_route")
repo = ScreeningRepository()

@router.post("/process", response_model=ScreeningResponse)
async def process_screening(
    doc_input: ValidatedInputDocument,
    pipeline: ScreeningPipelineOrchestrator = Depends(get_pipeline)
):
    """Triggers the full 14-module AI screening workflow."""
    screening_id = generate_screening_id()
    logger.info(f"Received screening request for doc {doc_input.document_id}, assigned ID: {screening_id}")
    
    result = await pipeline.execute_screening(screening_id, doc_input)
    return result

@router.get("/{screening_id}", response_model=dict)
async def get_screening_record(screening_id: str):
    """Retrieve full screening and audit log record by ID."""
    record = await repo.get_screening_by_id(screening_id)
    if not record:
        raise HTTPException(status_code=404, detail="Screening record not found.")
    return record

@router.post("/{screening_id}/adjudicate")
async def record_officer_decision(
    screening_id: str,
    adjudication: OfficerAdjudicationRequest
):
    """Module 13/14: Record official human officer decision (Clear, Review, Reject)."""
    success = await repo.update_officer_action(
        screening_id=screening_id,
        action=adjudication.decision,
        notes=f"Officer ID: {adjudication.officer_id} | {adjudication.justification_notes}"
    )
    if not success:
        raise HTTPException(status_code=404, detail="Screening record not found for adjudication.")
    
    return {
        "status": "success",
        "screening_id": screening_id,
        "officer_action": adjudication.decision.value,
        "message": "Officer decision recorded in immutable audit log."
    }
