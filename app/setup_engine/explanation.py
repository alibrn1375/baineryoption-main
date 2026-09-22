"""Decision explanation generator formatting clear, verifiable trade/no-trade rationale."""

from typing import List, Optional
from app.models.binary_decision import BinaryDecision, DecisionType, NoTradeReason
from app.models.setup import SetupEvaluation


class ExplainabilityEngine:
    """Generates transparent, structured multi-pillar justifications for every Decision Arbiter output."""

    @staticmethod
    def generate_explanation(
        decision: DecisionType,
        setup: Optional[SetupEvaluation],
        quality_score: float,
        ev_val: Optional[float],
        rejection_reasons: List[NoTradeReason],
        custom_notes: Optional[List[str]] = None
    ) -> str:
        """Synthesize structured text explanation."""
        lines: List[str] = [f"Decision: {decision.value}"]

        if decision in (DecisionType.CALL, DecisionType.PUT):
            lines.append(f"Setup: {setup.setup_name if setup else 'N/A'}")
            lines.append(f"Quality Score: {quality_score}/100")
            if ev_val is not None:
                lines.append(f"Expected Value (EV): +${ev_val:.3f} per $1 risked")

            lines.append("\nSupporting Factors:")
            if setup and setup.conditions_met:
                for cond in setup.conditions_met:
                    lines.append(f"  ✓ {cond}")
            if custom_notes:
                for note in custom_notes:
                    lines.append(f"  ✓ {note}")

        else:
            lines.append("\nOperational Rejection Reasons:")
            for r in rejection_reasons:
                lines.append(f"  ✗ [{r.value}]")

            if setup and setup.conditions_failed:
                lines.append("\nUnsatisfied Setup Criteria:")
                for cf in setup.conditions_failed:
                    lines.append(f"  - {cf}")

            if custom_notes:
                lines.append("\nRisk Context Flags:")
                for note in custom_notes:
                    lines.append(f"  - {note}")

        return "\n".join(lines)
