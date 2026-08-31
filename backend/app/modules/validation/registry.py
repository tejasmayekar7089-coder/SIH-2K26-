from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import RuleEvaluation, RuleStatus
from app.core.logging import get_logger

logger = get_logger("validation_registry")

class BaseValidationRule(ABC):
    """Abstract base class for all deterministic validation rules."""

    rule_id: str
    rule_name: str
    category: str

    @abstractmethod
    def evaluate(self,
                 extraction: ExtractionResult,
                 mrz: Optional[MRZResult] = None,
                 metadata: Optional[MetadataResult] = None,
                 quality: Optional[QualityResult] = None) -> RuleEvaluation:
        """Evaluates input data deterministically and returns a RuleEvaluation."""
        pass

class DocumentValidatorRegistry:
    """Central configurable rule registry mapping document categories to validation rules."""

    def __init__(self):
        self._registry: Dict[DocumentCategory, List[BaseValidationRule]] = {
            DocumentCategory.AADHAAR: [],
            DocumentCategory.DRIVING_LICENSE: [],
            DocumentCategory.DRIVING_LICENCE: [],
            DocumentCategory.PASSPORT: [],
            DocumentCategory.UNKNOWN: []
        }

    def register_rule(self, category: DocumentCategory, rule: BaseValidationRule) -> None:
        """Registers a rule for a specific document category."""
        if category not in self._registry:
            self._registry[category] = []
        self._registry[category].append(rule)
        logger.info(f"Registered validation rule '{rule.rule_id}' ({rule.rule_name}) for category '{category.value}'")

    def get_rules_for_category(self, category: DocumentCategory) -> List[BaseValidationRule]:
        """Returns the list of registered validation rules for the given category."""
        rules = self._registry.get(category, [])
        if category == DocumentCategory.DRIVING_LICENCE and not rules:
            rules = self._registry.get(DocumentCategory.DRIVING_LICENSE, [])
        return rules
