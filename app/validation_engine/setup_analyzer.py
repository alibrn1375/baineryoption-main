"""Detailed setup performance analyzer breaking down results by session, regime, and volatility."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.market_context import MarketContext
from app.models.setup import SetupType
from app.validation_engine.binary_simulator import BinarySimulationResult, SimulationOutcome


class SetupConditionBreakdown(BaseModel):
    """Performance metrics segmented by specific environmental conditions."""
    condition_name: str = Field(..., description="Segment name (e.g. Session: LONDON, Regime: TRENDING)")
    sample_size: int = Field(..., description="Total trades in segment")
    wins: int = Field(..., description="Wins in segment")
    win_rate: float = Field(..., description="Segment win rate")
    net_pnl: float = Field(..., description="Segment Net PnL")

    model_config = {
        "frozen": True
    }


class SetupStatistics(BaseModel):
    """Aggregate multi-dimensional performance statistics for a specific setup archetype."""
    setup_type: SetupType = Field(..., description="Target setup archetype")
    setup_name: str = Field(..., description="Setup human-readable name")
    sample_size: int = Field(..., description="Total executed occurrences")
    win_rate: float = Field(..., description="Overall win rate")
    net_pnl: float = Field(..., description="Total net PnL")
    session_breakdown: Dict[str, SetupConditionBreakdown] = Field(default_factory=dict, description="Session segments")
    regime_breakdown: Dict[str, SetupConditionBreakdown] = Field(default_factory=dict, description="Regime segments")
    best_conditions: List[str] = Field(default_factory=list, description="Top performing environmental parameters")
    worst_conditions: List[str] = Field(default_factory=list, description="Worst performing environmental parameters")

    model_config = {
        "frozen": True
    }


class SetupPerformanceAnalyzer:
    """Analyzes and isolates edge stability across market regimes, sessions, and volatility tiers."""

    @staticmethod
    def analyze_setup(
        setup_type: SetupType,
        setup_name: str,
        trades: List[BinarySimulationResult],
        contexts: List[MarketContext]
    ) -> SetupStatistics:
        """Segment trade outcomes across session, regime, and volatility conditions."""
        if not trades:
            return SetupStatistics(
                setup_type=setup_type,
                setup_name=setup_name,
                sample_size=0,
                win_rate=0.0,
                net_pnl=0.0
            )

        total = len(trades)
        wins = sum(1 for t in trades if t.outcome == SimulationOutcome.WIN)
        wr = wins / total if total > 0 else 0.0
        net_pnl = float(sum(t.pnl for t in trades))

        # Session Segmentation
        session_groups: Dict[str, List[BinarySimulationResult]] = {}
        regime_groups: Dict[str, List[BinarySimulationResult]] = {}

        for t, ctx in zip(trades, contexts):
            s_name = ctx.session.name.value
            r_name = ctx.regime.state.value

            session_groups.setdefault(s_name, []).append(t)
            regime_groups.setdefault(r_name, []).append(t)

        s_breakdown: Dict[str, SetupConditionBreakdown] = {}
        for s_name, s_trades in session_groups.items():
            s_wins = sum(1 for tr in s_trades if tr.outcome == SimulationOutcome.WIN)
            s_breakdown[s_name] = SetupConditionBreakdown(
                condition_name=f"Session: {s_name}",
                sample_size=len(s_trades),
                wins=s_wins,
                win_rate=round(s_wins / len(s_trades), 4),
                net_pnl=round(sum(tr.pnl for tr in s_trades), 2)
            )

        r_breakdown: Dict[str, SetupConditionBreakdown] = {}
        for r_name, r_trades in regime_groups.items():
            r_wins = sum(1 for tr in r_trades if tr.outcome == SimulationOutcome.WIN)
            r_breakdown[r_name] = SetupConditionBreakdown(
                condition_name=f"Regime: {r_name}",
                sample_size=len(r_trades),
                wins=r_wins,
                win_rate=round(r_wins / len(r_trades), 4),
                net_pnl=round(sum(tr.pnl for tr in r_trades), 2)
            )

        # Identify best / worst conditions
        best_cond: List[str] = []
        worst_cond: List[str] = []

        for name, b in {**s_breakdown, **r_breakdown}.items():
            if b.sample_size >= 5 and b.win_rate >= 0.65:
                best_cond.append(f"{name} ({b.win_rate*100:.1f}%, n={b.sample_size})")
            elif b.sample_size >= 5 and b.win_rate <= 0.45:
                worst_cond.append(f"{name} ({b.win_rate*100:.1f}%, n={b.sample_size})")

        return SetupStatistics(
            setup_type=setup_type,
            setup_name=setup_name,
            sample_size=total,
            win_rate=round(wr, 4),
            net_pnl=round(net_pnl, 2),
            session_breakdown=s_breakdown,
            regime_breakdown=r_breakdown,
            best_conditions=best_cond,
            worst_conditions=worst_cond
        )
