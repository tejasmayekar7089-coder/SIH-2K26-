from fastapi import APIRouter
from app.schemas.face import FaceResult
from app.schemas.document import ValidatedInputDocument
from app.schemas.extraction import ExtractionResult
from app.modules.face.service import FaceVerificationService

router = APIRouter(prefix="/face", tags=["Module 8: Biometric Face Verification"])
face_service = FaceVerificationService()

@router.post("/verify-1to1", response_model=FaceResult)
async def verify_face_1to1(
    doc_input: ValidatedInputDocument,
    extraction: ExtractionResult
):
    """Standalone 1:1 Face Verification endpoint."""
    return face_service.verify_identity(doc_input, extraction)
