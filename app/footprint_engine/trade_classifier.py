"""Trade classification engine for order flow aggressor side detection without guessing."""

from typing import Optional
from pydantic import BaseModel, Field
from app.models.tick import Tick, TradeSide


class TradeClassification(BaseModel):
    """Result of trade side classification."""
    side: TradeSide = Field(..., description="Determined trade side (BUY, SELL, UNKNOWN)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in classification")
    reason: str = Field(..., description="Explanation of classification rationale")

    model_config = {
        "frozen": True
    }


class TradeClassifier:
    """Classifies trades into BUY, SELL, or UNKNOWN strictly using verified BBO book quotes.
    
    Rules:
    1. If explicit trade side is provided in feed and valid -> Use explicit side (confidence=1.0)
    2. If Ask price is provided and trade price >= Ask -> BUY (confidence=1.0)
    3. If Bid price is provided and trade price <= Bid -> SELL (confidence=1.0)
    4. If Bid and Ask are provided and price is between them -> Quote Rule / Midpoint (confidence=0.7)
    5. If Bid and Ask are both unavailable -> Return UNKNOWN (confidence=0.0). NEVER guess or synthesize.
    """

    def classify(self, tick: Tick) -> TradeClassification:
        """Classify a single validated tick."""
        # 1. Explicit verified side from source feed
        if tick.trade_side in (TradeSide.BUY, TradeSide.SELL):
            return TradeClassification(
                side=tick.trade_side,
                confidence=1.0,
                reason="Explicit aggressor side from data provider"
            )

        price = tick.price
        bid = tick.bid
        ask = tick.ask

        # 2. Both Bid and Ask missing -> UNKNOWN (Do not guess)
        if bid is None and ask is None:
            return TradeClassification(
                side=TradeSide.UNKNOWN,
                confidence=0.0,
                reason="Bid and Ask quotes are unavailable; cannot classify without guessing"
            )

        # 3. Direct Ask execution (Aggressive Buy)
        if ask is not None and price >= ask:
            return TradeClassification(
                side=TradeSide.BUY,
                confidence=1.0,
                reason=f"Executed price {price} >= Ask {ask}"
            )

        # 4. Direct Bid execution (Aggressive Sell)
        if bid is not None and price <= bid:
            return TradeClassification(
                side=TradeSide.SELL,
                confidence=1.0,
                reason=f"Executed price {price} <= Bid {bid}"
            )

        # 5. Inside the spread (Midpoint inference)
        if bid is not None and ask is not None:
            mid = (bid + ask) / 2.0
            if price > mid:
                return TradeClassification(
                    side=TradeSide.BUY,
                    confidence=0.7,
                    reason=f"Executed price {price} > Midpoint {mid}"
                )
            elif price < mid:
                return TradeClassification(
                    side=TradeSide.SELL,
                    confidence=0.7,
                    reason=f"Executed price {price} < Midpoint {mid}"
                )

        # Fallback when exact side cannot be firmly established
        return TradeClassification(
            side=TradeSide.UNKNOWN,
            confidence=0.0,
            reason=f"Price {price} inside spread with insufficient clarity"
        )
