import json
from datetime import datetime, timezone
from typing import Optional
from app.schemas.screening import ScreeningResponse, OfficerAction
from app.schemas.audit import AuditLogEntry, OfficerAdjudicationRequest
from app.schemas.risk import RiskLevel
from app.database.repositories import ScreeningRepository
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("audit_trail")

class AuditTrailService:
    def __init__(self, repository: Optional[ScreeningRepository] = None):
        self.repo = repository or ScreeningRepository()

    async def log_screening_event(self, screening: ScreeningResponse) -> None:
        """Module 14: Record immutable screening event log."""
        logger.info(f"Writing versioned audit log for screening: {screening.screening_id}")
        await self.repo.save_screening(screening)

    async def record_officer_adjudication(
        self,
        screening_id: str,
        adjudication: OfficerAdjudicationRequest
    ) -> bool:
        """Record human officer decision and notes."""
        logger.info(f"Officer {adjudication.officer_id} adjudicated {screening_id} as {adjudication.decision.value}")
        return await self.repo.update_officer_action(
            screening_id=screening_id,
            action=adjudication.decision,
            notes=f"Officer: {adjudication.officer_id} | {adjudication.justification_notes}"
        )
