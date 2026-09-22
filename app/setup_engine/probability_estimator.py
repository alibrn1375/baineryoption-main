"""Empirical probability estimator using Wilson Score Confidence Intervals with small sample penalties."""

import math
from typing import Dict, Optional, Tuple
from pydantic import BaseModel, Field


class ProbabilityEstimate(BaseModel):
    """Statistical historical probability estimate with Wilson Confidence Interval."""
    sample_size: int = Field(..., ge=0, description="Total historical occurrences observed")
    wins: int = Field(..., ge=0, description="Successful historical outcomes")
    historical_rate: float = Field(..., ge=0.0, le=1.0, description="Sample win rate (wins / total)")
    wilson_lower: float = Field(..., ge=0.0, le=1.0, description="Lower Wilson confidence bound at 95% confidence")
    wilson_upper: float = Field(..., ge=0.0, le=1.0, description="Upper Wilson confidence bound at 95% confidence")
    reliability: float = Field(..., ge=0.0, le=1.0, description="Sample size adequacy penalty [0.0 - 1.0]")
    conservative_probability: float = Field(..., ge=0.0, le=1.0, description="Probability used for EV calculation")

    model_config = {
        "frozen": True
    }


class ProbabilityEstimator:
    """Calculates historical setup win rates penalized by sample size via Wilson intervals."""

    def __init__(self, z_score: float = 1.96, min_sample_adequate: int = 30) -> None:
        self.z = z_score  # 1.96 corresponds to 95% confidence
        self.min_sample_adequate = min_sample_adequate

    def calculate_wilson_interval(self, wins: int, total: int) -> Tuple[float, float]:
        """Compute Wilson Score Interval for binomial distribution proportion."""
        if total <= 0:
            return 0.0, 0.0

        p = wins / total
        z = self.z
        z_sq = z * z

        denominator = 1.0 + (z_sq / total)
        center_adj = p + (z_sq / (2.0 * total))
        spread = z * math.sqrt((p * (1.0 - p) / total) + (z_sq / (4.0 * total * total)))

        lower = max(0.0, (center_adj - spread) / denominator)
        upper = min(1.0, (center_adj + spread) / denominator)

        return round(lower, 4), round(upper, 4)

    def estimate(self, wins: int, total: int) -> ProbabilityEstimate:
        """Calculate statistical probability with adequacy discount."""
        if total == 0:
            return ProbabilityEstimate(
                sample_size=0,
                wins=0,
                historical_rate=0.0,
                wilson_lower=0.0,
                wilson_upper=0.0,
                reliability=0.0,
                conservative_probability=0.0
            )

        raw_rate = wins / total
        lower, upper = self.calculate_wilson_interval(wins, total)

        # Reliability penalty: S-curve transition from 0 to 1 as samples reach adequate threshold
        reliability = min(1.0, total / float(self.min_sample_adequate))

        # Use conservative lower Wilson bound, especially on smaller samples
        conservative_p = lower if total < self.min_sample_adequate else (0.7 * lower + 0.3 * raw_rate)

        return ProbabilityEstimate(
            sample_size=total,
            wins=wins,
            historical_rate=round(raw_rate, 4),
            wilson_lower=lower,
            wilson_upper=upper,
            reliability=round(reliability, 2),
            conservative_probability=round(conservative_p, 4)
        )
