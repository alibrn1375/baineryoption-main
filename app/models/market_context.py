"""Unified Market Context domain model combining all environmental observation layers."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.models.footprint import FootprintQuality
from app.models.liquidity import LiquidityEvent, LiquidityZone
from app.models.market_structure import MarketStructureState, StructureState


class MarketStructure(str, Enum):
    """Legacy flat structure labels accepted by the original domain contract."""
    BULLISH_MSS = "BULLISH_MSS"
    BEARISH_MSS = "BEARISH_MSS"


class MarketRegimeState(str, Enum):
    """Macro-structural regime state of the market."""
    TRENDING_BULLISH = "TRENDING_BULLISH"
    TRENDING_BEARISH = "TRENDING_BEARISH"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    TRANSITION = "TRANSITION"


class MarketRegime(BaseModel):
    """Regime classification snapshot."""
    state: MarketRegimeState = Field(..., description="Current regime classification")
    strength: float = Field(default=1.0, ge=0.0, description="Normalized regime intensity")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Classification confidence")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Underlying indicators (ADX, ATR, Efficiency)")

    model_config = {
        "frozen": True
    }

    def __eq__(self, other: object) -> bool:
        if isinstance(other, MarketRegimeState):
            return self.state == other
        return super().__eq__(other)


class TradingSessionName(str, Enum):
    """Active global trading session."""
    ASIA = "ASIA"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OVERLAP_LONDON_NY = "OVERLAP_LONDON_NY"
    POST_MARKET = "POST_MARKET"
    CLOSED = "CLOSED"


class TradingSession(BaseModel):
    """Active session metadata."""
    name: TradingSessionName = Field(..., description="Active session name")
    start_time: str = Field(..., description="Session start UTC string HH:MM:SS")
    end_time: str = Field(..., description="Session end UTC string HH:MM:SS")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Session validity score")

    model_config = {
        "frozen": True
    }


class VolatilityLevel(str, Enum):
    """Categorical volatility condition."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class VolatilityState(BaseModel):
    """Comprehensive volatility measurement."""
    level: VolatilityLevel = Field(..., description="Categorical volatility level")
    percentile: float = Field(..., ge=0.0, le=100.0, description="Rolling historical percentile rank")
    atr_value: float = Field(..., ge=0.0, description="Average True Range in price terms")
    candle_efficiency: float = Field(default=1.0, ge=0.0, description="Body progression vs range ratio")

    model_config = {
        "frozen": True
    }


class NewsRiskLevel(str, Enum):
    """Risk severity of macro events."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NewsState(BaseModel):
    """Real-time macroeconomic quarantine and news risk state."""
    event_active: bool = Field(..., description="True if within the news risk window")
    risk_level: NewsRiskLevel = Field(default=NewsRiskLevel.NONE, description="Assessed news risk level")
    blocked: bool = Field(..., description="True if news quarantine enforces an operational halt")
    active_events: List[str] = Field(default_factory=list, description="Titles of proximate high-impact events")
    minutes_to_next: Optional[int] = Field(default=None, description="Minutes until proximate scheduled release")
    reason: Optional[str] = Field(default=None, description="Reason for quarantine or caution")

    model_config = {
        "frozen": True
    }


class MarketContext(BaseModel):
    """Comprehensive environmental context snapshot for a 5M timeframe bar.
    
    NOTE: This is strictly an objective measurement and environmental observation object.
    It contains NO trade triggers, signals, or direction predictions.
    """
    timestamp: datetime = Field(..., description="Timestamp of the context bar (UTC)")
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    timeframe: str = Field(default="5m", description="Bar timeframe")

    # Environmental sub-components
    structure: MarketStructureState = Field(default=None, description="Market structure, swings, and BOS/MSS events")
    active_liquidity_zones: List[LiquidityZone] = Field(default_factory=list, description="Surrounding active resting liquidity pools")
    recent_liquidity_event: Optional[LiquidityEvent] = Field(default=None, description="Most recent interaction/sweep with liquidity")
    regime: MarketRegime = Field(default=None, description="Market regime (Trending, Ranging, Volatility)")
    session: TradingSession = Field(default=None, description="Active trading session context")
    volatility: VolatilityState = Field(..., description="Real-time volatility and ATR metrics")
    news: NewsState = Field(default=None, validation_alias="news", description="Macro event quarantine state")
    data_quality: FootprintQuality = Field(default=FootprintQuality.HIGH_PRECISION, description="Underlying data integrity")
    overall_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite environmental confidence score")

    @property
    def news_state(self) -> NewsRiskLevel:
        """Legacy accessor returning the flat news risk state."""
        return self.news.risk_level

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_inputs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values = dict(values)
        timestamp = values.get("timestamp", datetime.now())
        symbol = values.get("symbol", "UNKNOWN")
        structure = values.get("structure")
        if isinstance(structure, MarketStructure):
            values["structure"] = MarketStructureState(
                timestamp=timestamp,
                symbol=symbol,
                current_state=(
                    StructureState.TREND_UP
                    if structure == MarketStructure.BULLISH_MSS
                    else StructureState.TREND_DOWN
                ),
            )
        elif structure is None:
            values["structure"] = MarketStructureState(timestamp=timestamp, symbol=symbol)
        regime = values.get("regime")
        if isinstance(regime, MarketRegimeState):
            values["regime"] = MarketRegime(state=regime)
        elif regime is None:
            values["regime"] = MarketRegime(state=MarketRegimeState.RANGING)
        session = values.get("session")
        if isinstance(session, TradingSessionName):
            values["session"] = TradingSession(name=session, start_time="00:00:00", end_time="23:59:59")
        elif session is None:
            values["session"] = TradingSession(name=TradingSessionName.CLOSED, start_time="00:00:00", end_time="23:59:59")
        volatility = values.get("volatility")
        if isinstance(volatility, VolatilityLevel):
            values["volatility"] = VolatilityState(level=volatility, percentile=50.0, atr_value=0.0)
        news = values.get("news", values.get("news_state"))
        if isinstance(news, NewsRiskLevel):
            values["news"] = NewsState(
                event_active=news != NewsRiskLevel.NONE,
                risk_level=news,
                blocked=news in (NewsRiskLevel.HIGH, NewsRiskLevel.CRITICAL),
            )
        elif news is None:
            values["news"] = NewsState(event_active=False, blocked=False)
        if "news" not in values and "news_state" in values:
            values["news"] = values.pop("news_state")
        if "data_quality" not in values and "data_quality_score" in values:
            values["data_quality"] = FootprintQuality.HIGH_PRECISION
        return values

    model_config = {
        "frozen": True
    }

MarketRegimeStateAlias = MarketRegimeState

TradingSessionNameAlias = TradingSessionName

VolatilityLevelAlias = VolatilityLevel

NewsRiskLevelAlias = NewsRiskLevel

MarketRegime.TRENDING_BULLISH = MarketRegimeState.TRENDING_BULLISH
MarketRegime.TRENDING_BEARISH = MarketRegimeState.TRENDING_BEARISH
TradingSession.LONDON = TradingSessionName.LONDON
TradingSession.NEW_YORK = TradingSessionName.NEW_YORK
VolatilityState.NORMAL = VolatilityLevel.NORMAL
NewsState.CLEAR = NewsRiskLevel.NONE

