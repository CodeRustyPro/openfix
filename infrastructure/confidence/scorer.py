"""Confidence and risk scoring for generated patches.

Calculates a confidence score (0-100) and risk rating (Low/Medium/High) based on:
- Triage priority score
- Issue complexity
- Validation results
- Number of repair attempts
- Code metrics (if available)
"""

from typing import Dict, Any


class ConfidenceScorer:
    """Calculate confidence scores for generated patches."""

    def __init__(self):
        self.weights = {
            "triage_score": 0.25,  # Higher triage score = higher confidence
            "complexity": 0.20,  # Lower complexity = higher confidence
            "validation": 0.35,  # Passed validation = higher confidence
            "repair_attempts": 0.20,  # Fewer attempts = higher confidence
        }

    def calculate_confidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence score and risk rating.

        Args:
            data: Dict containing:
                - triage_score: 1-10 priority score from triage
                - complexity: "low", "medium", "high"
                - validation_passed: bool
                - repair_attempts: int (0 = first try succeeded)
                - patch_generated: bool

        Returns:
            Dict with:
                - confidence_score: 0-100
                - risk_rating: "Low", "Medium", "High"
                - factors: breakdown of score components
        """
        if not data.get("patch_generated"):
            return {
                "confidence_score": 0,
                "risk_rating": "High",
                "factors": {"reason": "No patch generated"},
            }

        # Calculate component scores (0-100 each)
        triage_component = self._score_triage(data.get("triage_score", 5))
        complexity_component = self._score_complexity(data.get("complexity", "medium"))
        validation_component = self._score_validation(
            data.get("validation_passed", False)
        )
        repair_component = self._score_repair_attempts(data.get("repair_attempts", 0))

        # Weighted average
        confidence_score = (
            triage_component * self.weights["triage_score"]
            + complexity_component * self.weights["complexity"]
            + validation_component * self.weights["validation"]
            + repair_component * self.weights["repair_attempts"]
        )

        # Determine risk rating
        risk_rating = self._determine_risk(confidence_score, data)

        return {
            "confidence_score": round(confidence_score, 1),
            "risk_rating": risk_rating,
            "factors": {
                "triage": triage_component,
                "complexity": complexity_component,
                "validation": validation_component,
                "repair_attempts": repair_component,
            },
        }

    def _score_triage(self, score: int) -> float:
        """Convert triage score (1-10) to confidence (0-100)."""
        # Linear mapping: 1->20, 10->100
        return min(100, max(0, 20 + (score - 1) * 8.9))

    def _score_complexity(self, complexity: str) -> float:
        """Convert complexity to confidence score."""
        mapping = {"low": 90, "medium": 60, "high": 30, "unknown": 40}
        return mapping.get(complexity.lower(), 40)

    def _score_validation(self, passed: bool) -> float:
        """Score based on validation results."""
        return 100 if passed else 20  # Heavy penalty for validation failure

    def _score_repair_attempts(self, attempts: int) -> float:
        """Score based on repair iterations needed."""
        if attempts == 0:
            return 100  # First try success
        elif attempts == 1:
            return 70  # One repair needed
        elif attempts == 2:
            return 40  # Two repairs
        else:
            return 20  # Many repairs

    def _determine_risk(self, confidence_score: float, data: Dict[str, Any]) -> str:
        """Determine risk rating based on confidence and other factors."""
        # High confidence + validation passed = Low risk
        if confidence_score >= 75 and data.get("validation_passed"):
            return "Low"

        # Low confidence or validation failed = High risk
        if confidence_score < 50 or not data.get("validation_passed"):
            return "High"

        # Everything else = Medium risk
        return "Medium"

    def get_recommendation(self, confidence_data: Dict[str, Any]) -> str:
        """Get human-readable recommendation based on score."""
        score = confidence_data["confidence_score"]
        risk = confidence_data["risk_rating"]

        if score >= 75 and risk == "Low":
            return "✅ High confidence - Recommended for auto-merge"
        elif score >= 60 and risk == "Medium":
            return "⚠️ Medium confidence - Review recommended"
        else:
            return "❌ Low confidence - Manual review required"
