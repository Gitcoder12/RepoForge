"""
Plan Finalizer – merges agent suggestions into a final actionable plan.
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PlanFinalizer:
    """Merges agent suggestions and produces a final plan."""

    @staticmethod
    def finalize(orchestrator_result: Dict[str, Any],
                 original_selected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes orchestrator output and the original V4 selected improvement,
        and returns an enhanced plan.
        """
        suggestions = orchestrator_result.get("combined_suggestions", [])
        agent_results = orchestrator_result.get("agent_results", [])

        if not suggestions:
            # No agent suggestions – return original
            return original_selected

        # Build enhanced plan
        enhanced = {
            "original_improvement": original_selected,
            "agent_suggestions": suggestions,
            "plan_summary": f"Enhanced with {len(suggestions)} agent suggestions",
            "agents_contributing": [r.get("agent") for r in agent_results if r.get("suggestions")]
        }

        # If original is None, create a new improvement from suggestions
        if original_selected is None:
            enhanced["type"] = "agent_suggested"
            enhanced["description"] = " ; ".join(suggestions[:3])
            enhanced["severity_score"] = 0.5
            enhanced["effort_estimate"] = 0.5
            enhanced["confidence"] = 0.5

        return enhanced