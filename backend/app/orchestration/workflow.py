from app.orchestration.screening_pipeline import ScreeningPipelineOrchestrator

pipeline_instance = ScreeningPipelineOrchestrator()

def get_pipeline() -> ScreeningPipelineOrchestrator:
    """Returns singleton pipeline orchestrator instance."""
    return pipeline_instance
