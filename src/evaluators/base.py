"""Base classes and data models for RegShield evaluators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class EvaluationResult:
    """Represents the standardized evaluation outcome for any safety test."""
    category: str
    passed: bool
    risk_detected: bool
    reason: str
    evidence: List[str] = field(default_factory=list)
    score: float = 1.0  # 1.0 = safe/pass, 0.0 = unsafe/fail (or toxicity metric)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the evaluation result into a serializable dictionary."""
        return {
            "category": self.category,
            "passed": self.passed,
            "result": "PASS" if self.passed else "FAIL",
            "risk_detected": self.risk_detected,
            "reason": self.reason,
            "evidence": self.evidence,
            "score": round(self.score, 3),
            "metadata": self.metadata
        }


class BaseEvaluator(ABC):
    """Abstract base class for all risk evaluators in RegShield."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(self, prompt: str, response: str, **kwargs) -> EvaluationResult:
        """
        Evaluates an LLM response against a given prompt.

        Args:
            prompt: The input user/adversarial prompt.
            response: The LLM's generated response.
            **kwargs: Optional additional context (e.g. expected entity, target category).

        Returns:
            An EvaluationResult instance.
        """
        pass
