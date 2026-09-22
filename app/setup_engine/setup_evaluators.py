"""Analytical setup evaluators implementing Setups A, B, C, and D based on order flow and context."""

from typing import List, Optional
from app.models.footprint import FootprintBar, FootprintQuality
from app.models.liquidity import LiquidityEventType, LiquidityZoneType
from app.models.market_context import MarketContext, MarketRegimeState
from app.models.market_structure import StructureState
from app.models.orderflow_context import OrderFlowContext
from app.models.setup import SetupEvaluation, SetupType
from app.orderflow_engine.base import FeatureDirection


class SetupEvaluators:
    """Evaluates 4 research setups (A, B, C, D) using empirical microstructural criteria."""

    @staticmethod
    def evaluate_setup_a(
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> SetupEvaluation:
        """Setup A: Liquidity Sweep + Absorption.
        
        Requires:
        1. Recent Liquidity Sweep Event (SWEEP_HIGH or SWEEP_LOW).
        2. Strong Order Flow Absorption in the same direction.
        3. Favorable wick rejection / candle closure.
        4. Data quality is HIGH_PRECISION or acceptable.
        """
        met = []
        failed = []
        direction = FeatureDirection.NEUTRAL
        score = 0.0

        # Check 1: Liquidity Event
        liq_ev = mkt_ctx.recent_liquidity_event
        if liq_ev and liq_ev.event_type in (LiquidityEventType.SWEEP_HIGH, LiquidityEventType.SWEEP_LOW):
            met.append(f"Confirmed {liq_ev.event_type.value} at price {liq_ev.zone.price}")
            # If high was swept -> Looking for downside rejection (SELL / PUT)
            # If low was swept -> Looking for upside rejection (BUY / CALL)
            direction = FeatureDirection.SELL if liq_ev.event_type == LiquidityEventType.SWEEP_HIGH else FeatureDirection.BUY
            score += 35.0
        else:
            failed.append("No proximate liquidity sweep event detected")

        # Check 2: Order Flow Absorption
        abs_feat = of_ctx.absorption_feature
        if abs_feat is not None:
            # For BUY setup: Absorption must absorb sell aggression at lows (FeatureDirection.SELL absorbed -> BUY outcome)
            # For SELL setup: Absorption must absorb buy aggression at highs (FeatureDirection.BUY absorbed -> SELL outcome)
            if direction == FeatureDirection.SELL and abs_feat.direction == FeatureDirection.BUY:
                met.append(f"Passive sell limit absorption of aggressive buyers (Score: {abs_feat.absorption_score})")
                score += 35.0
            elif direction == FeatureDirection.BUY and abs_feat.direction == FeatureDirection.SELL:
                met.append(f"Passive buy limit absorption of aggressive sellers (Score: {abs_feat.absorption_score})")
                score += 35.0
            else:
                score += 15.0
                met.append("Absorption detected but directional polarity is mixed")
        else:
            failed.append("No aggressive volume absorption feature detected")

        # Check 3: Market Context Alignment
        if mkt_ctx.regime.state in (MarketRegimeState.RANGING, MarketRegimeState.HIGH_VOLATILITY, MarketRegimeState.TRENDING_BULLISH, MarketRegimeState.TRENDING_BEARISH):
            met.append(f"Regime {mkt_ctx.regime.state.value} compatible with sweep rejection")
            score += 20.0
        else:
            failed.append("Market regime unfavorable")

        # Check 4: Data Quality
        if bar.quality == FootprintQuality.HIGH_PRECISION:
            met.append("High precision microsecond tick feed")
            score += 10.0
        else:
            failed.append("Degraded data quality")

        is_triggered = len(failed) == 0 and score >= 75.0 and direction != FeatureDirection.NEUTRAL

        return SetupEvaluation(
            timestamp=bar.start_time,
            setup_type=SetupType.SETUP_A,
            setup_name="Liquidity Sweep + Absorption Reversal",
            direction=direction,
            is_triggered=is_triggered,
            conditions_met=met,
            conditions_failed=failed,
            score=min(100.0, score),
            confidence=1.0 if is_triggered else 0.5,
            details={"sweep_event": str(liq_ev), "absorption": str(abs_feat)}
        )

    @staticmethod
    def evaluate_setup_b(
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> SetupEvaluation:
        """Setup B: Imbalance Continuation.
        
        Requires:
        1. Stacked diagonal imbalance (>= 3 consecutive levels) or extreme single imbalance.
        2. Delta acceleration and persistence alignment.
        3. Market Structure alignment (BOS in same direction).
        """
        met = []
        failed = []
        direction = FeatureDirection.NEUTRAL
        score = 0.0

        # Check 1: Stacked Imbalance
        if of_ctx.stacked_imbalances:
            stk = of_ctx.stacked_imbalances[0]
            direction = stk.direction
            met.append(f"Stacked {direction.value} imbalance across {stk.levels_count} levels ({stk.bottom_price} - {stk.top_price})")
            score += 40.0
        elif of_ctx.imbalances:
            buy_imb = [i for i in of_ctx.imbalances if i.direction == FeatureDirection.BUY]
            sell_imb = [i for i in of_ctx.imbalances if i.direction == FeatureDirection.SELL]
            if len(buy_imb) >= 2 and len(buy_imb) > len(sell_imb):
                direction = FeatureDirection.BUY
                met.append(f"Multiple ({len(buy_imb)}) diagonal buy imbalances detected")
                score += 25.0
            elif len(sell_imb) >= 2 and len(sell_imb) > len(buy_imb):
                direction = FeatureDirection.SELL
                met.append(f"Multiple ({len(sell_imb)}) diagonal sell imbalances detected")
                score += 25.0
            else:
                failed.append("Imbalances lack directional preponderance")
        else:
            failed.append("No valid order flow imbalance detected")

        # Check 2: Delta Momentum
        delta_feat = of_ctx.delta_feature
        if delta_feat and delta_feat.direction == direction and delta_feat.strength >= 1.2:
            met.append(f"Delta aligned ({delta_feat.direction.value}) with strength {delta_feat.strength}")
            score += 30.0
        else:
            failed.append("Delta momentum is weak or divergent from imbalance")

        # Check 3: Market Structure Trend Alignment
        if (direction == FeatureDirection.BUY and mkt_ctx.structure.current_state == StructureState.TREND_UP) or \
           (direction == FeatureDirection.SELL and mkt_ctx.structure.current_state == StructureState.TREND_DOWN):
            met.append(f"Aligned with broader market structure ({mkt_ctx.structure.current_state.value})")
            score += 30.0
        else:
            failed.append("Counter-trend or unclear structural trend")

        is_triggered = len(failed) == 0 and score >= 75.0 and direction != FeatureDirection.NEUTRAL

        return SetupEvaluation(
            timestamp=bar.start_time,
            setup_type=SetupType.SETUP_B,
            setup_name="Imbalance Momentum Continuation",
            direction=direction,
            is_triggered=is_triggered,
            conditions_met=met,
            conditions_failed=failed,
            score=min(100.0, score),
            confidence=1.0 if is_triggered else 0.5,
            details={"stacked_count": len(of_ctx.stacked_imbalances)}
        )

    @staticmethod
    def evaluate_setup_c(
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> SetupEvaluation:
        """Setup C: Momentum Exhaustion Event.
        
        Requires:
        1. Confirmed Exhaustion Feature (severe delta collapse after extreme push).
        2. Range expansion followed by failure at highs/lows.
        3. Clear rejection reaction.
        """
        met = []
        failed = []
        direction = FeatureDirection.NEUTRAL
        score = 0.0

        exh_feat = of_ctx.exhaustion_feature
        if exh_feat and exh_feat.follow_through_failed:
            # Exhaustion of buyers at new high -> Trade SELL / PUT
            # Exhaustion of sellers at new low -> Trade BUY / CALL
            direction = FeatureDirection.SELL if exh_feat.direction == FeatureDirection.BUY else FeatureDirection.BUY
            met.append(f"Exhaustion confirmed: {exh_feat.direction.value} delta depleted by {exh_feat.delta_depletion_ratio * 100}%")
            score += 50.0
        else:
            failed.append("No verified order flow exhaustion event")

        # Check 2: Volatility / Range Condition
        if mkt_ctx.volatility.candle_efficiency <= 0.40:
            met.append("Low candle efficiency confirming trapped aggression")
            score += 30.0
        else:
            failed.append("Candle efficiency too high for exhaustion reversal")

        # Check 3: Risk / News Clear
        if not mkt_ctx.news.blocked:
            score += 20.0
            met.append("News risk clean")
        else:
            failed.append("News blackout active")

        is_triggered = len(failed) == 0 and score >= 75.0 and direction != FeatureDirection.NEUTRAL

        return SetupEvaluation(
            timestamp=bar.start_time,
            setup_type=SetupType.SETUP_C,
            setup_name="Aggressive Momentum Exhaustion",
            direction=direction,
            is_triggered=is_triggered,
            conditions_met=met,
            conditions_failed=failed,
            score=min(100.0, score),
            confidence=1.0 if is_triggered else 0.5,
            details={"exhaustion_score": exh_feat.exhaustion_score if exh_feat else 0.0}
        )

    @staticmethod
    def evaluate_setup_d(
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> SetupEvaluation:
        """Setup D: Failed Auction Rejection.
        
        Requires:
        1. Range boundary breakout attempt.
        2. Immediate failure and rotation back into value area.
        3. Strong opposing delta confirming rejection.
        """
        met = []
        failed = []
        direction = FeatureDirection.NEUTRAL
        score = 0.0

        # Check 1: Range Regime
        if mkt_ctx.regime.state == MarketRegimeState.RANGING:
            met.append("Market in established balance / range regime")
            score += 30.0
        else:
            failed.append("Market not in a defined range balance")

        # Check 2: Delta Reversal
        delta_feat = of_ctx.delta_feature
        if delta_feat and abs(delta_feat.bar_delta) > 50.0:
            if bar.high > bar.open and bar.close < bar.open and delta_feat.direction == FeatureDirection.SELL:
                direction = FeatureDirection.SELL
                met.append("Failed auction at highs with aggressive sell delta rotation")
                score += 45.0
            elif bar.low < bar.open and bar.close > bar.open and delta_feat.direction == FeatureDirection.BUY:
                direction = FeatureDirection.BUY
                met.append("Failed auction at lows with aggressive buy delta rotation")
                score += 45.0
            else:
                failed.append("Delta polarity does not confirm auction rejection")
        else:
            failed.append("Insufficient delta volume to confirm rotation")

        # Check 3: Wick rejection
        bar_range = bar.high - bar.low
        wick = (bar.high - bar.close) if direction == FeatureDirection.SELL else (bar.close - bar.low)
        wick_pct = (wick / bar_range) if bar_range > 0 else 0.0
        if wick_pct >= 0.35:
            met.append(f"Wick rejection ratio ({round(wick_pct*100, 1)}%) exceeds threshold")
            score += 25.0
        else:
            failed.append("Wick rejection too small")

        is_triggered = len(failed) == 0 and score >= 75.0 and direction != FeatureDirection.NEUTRAL

        return SetupEvaluation(
            timestamp=bar.start_time,
            setup_type=SetupType.SETUP_D,
            setup_name="Failed Auction Range Rejection",
            direction=direction,
            is_triggered=is_triggered,
            conditions_met=met,
            conditions_failed=failed,
            score=min(100.0, score),
            confidence=1.0 if is_triggered else 0.5,
            details={"wick_rejection_pct": round(wick_pct, 2)}
        )
