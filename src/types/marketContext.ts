export type MarketRegimeType =
  | 'TREND_UP'
  | 'TREND_DOWN'
  | 'RANGE'
  | 'COMPRESSION'
  | 'EXPANSION'
  | 'TRANSITION'
  | 'UNKNOWN';

export type VolatilityLevel = 'LOW' | 'NORMAL' | 'HIGH' | 'EXTREME';

export type TradingSessionType = 'ASIAN' | 'LONDON' | 'NEW_YORK' | 'LONDON_NY_OVERLAP' | 'SESSION_CLOSED';

export type NewsRiskState = 'NORMAL' | 'ELEVATED' | 'BLOCKED' | 'POST_EVENT_REASSESSMENT';

export type StructureEventType = 'BOS_BULLISH' | 'BOS_BEARISH' | 'CHOCH_BULLISH' | 'CHOCH_BEARISH' | 'NONE';

export type LiquidityLevelType =
  | 'PREVIOUS_DAY_HIGH'
  | 'PREVIOUS_DAY_LOW'
  | 'SESSION_HIGH'
  | 'SESSION_LOW'
  | 'SWING_HIGH'
  | 'SWING_LOW'
  | 'EQUAL_HIGHS_EQH'
  | 'EQUAL_LOWS_EQL';

export interface SwingPoint {
  id: string;
  timestamp: number;
  price: number;
  type: 'SWING_HIGH' | 'SWING_LOW';
  strength: number; // 0 - 100
  timeframe: '5M' | '15M' | '1H';
  confirmedBarIndex: number;
}

export interface StructureEvent {
  id: string;
  type: StructureEventType;
  direction: 'BULLISH' | 'BEARISH';
  brokenPriceLevel: number;
  breakoutCandleTimestamp: number;
  strength: number; // 0 - 100
  confirmedClose: boolean;
  timeframe: '5M' | '15M' | '1H';
}

export interface LiquidityLevel {
  id: string;
  price: number;
  type: LiquidityLevelType;
  strength: number; // 0 - 100
  timeframe: '5M' | '15M' | '1H' | 'DAILY';
  createdTimestamp: number;
  isSwept: boolean;
  touchCount: number;
}

export interface LiquiditySweepEvent {
  id: string;
  direction: 'BULLISH_SWEEP' | 'BEARISH_SWEEP';
  sweptLevel: LiquidityLevel;
  sweepPrice: number;
  rejectionClosePrice: number;
  sweepDistanceTicks: number;
  rejectionDistanceTicks: number;
  timeOutsideLevelMs: number;
  volumeOnSweep: number;
  orderFlowConfirmed: boolean;
  strength: number; // 0 - 100
  timestamp: number;
}

export interface FailedAuctionEvent {
  id: string;
  direction: 'FAILED_BREAKOUT_HIGH' | 'FAILED_BREAKOUT_LOW';
  breakoutLevel: number;
  reversalPrice: number;
  deltaAtExtremum: number;
  volumeAtExtremum: number;
  strength: number; // 0 - 100
  timestamp: number;
}

export interface VolatilityState {
  level: VolatilityLevel;
  atr14: number;
  realizedVolPercent: number;
  candleRangePercentile: number;
  tickVelocityPerSecond: number;
  volumePercentile: number;
  confidence: number;
  timestamp: number;
}

export interface SessionState {
  currentSession: TradingSessionType;
  sessionOpenTime: string;
  sessionHigh: number;
  sessionLow: number;
  sessionVolume: number;
  sessionDurationMinutes: number;
  isOverlapActive: boolean;
  historicalVolatilityProfile: 'HIGH_MOMENTUM' | 'BALANCED_RANGE' | 'CHOPPY_ACCUMULATION';
}

export interface NewsEvent {
  id: string;
  name: string;
  timestamp: number;
  currency: 'USD' | 'EUR' | 'ALL';
  importance: 'HIGH' | 'CRITICAL' | 'MEDIUM';
  forecast?: string;
  actual?: string;
  previous?: string;
}

export interface NewsRiskEnvironment {
  state: NewsRiskState;
  minutesToNextEvent: number | null;
  minutesSinceLastEvent: number | null;
  activeEventName: string | null;
  tradingAllowed: boolean;
  reason: string;
}

export interface MultiTimeframeContext {
  primaryTimeframe5M: {
    regime: MarketRegimeType;
    structure: 'BULLISH_TREND' | 'BEARISH_TREND' | 'RANGE_BOUND' | 'TRANSITION';
    latestEvent: StructureEventType;
  };
  contextTimeframe15M: {
    regime: MarketRegimeType;
    structure: 'BULLISH_TREND' | 'BEARISH_TREND' | 'PULLBACK' | 'RANGE_BOUND';
  };
  macroTimeframe1H: {
    regime: MarketRegimeType;
    structure: 'BULLISH_TREND' | 'BEARISH_TREND' | 'RANGE_BOUND';
  };
  alignment: 'BULLISH_ALIGNED' | 'BEARISH_ALIGNED' | 'MIXED_CONFLICT' | 'NEUTRAL_RANGE';
  alignmentScore: number; // 0 - 100
}

export interface MarketContext {
  timestamp: number;
  symbol: string;
  regimeState: {
    state: MarketRegimeType;
    confidence: number;
    trendPersistenceBars: number;
  };
  mtfContext: MultiTimeframeContext;
  swings: SwingPoint[];
  structureEvents: StructureEvent[];
  activeLiquidityLevels: LiquidityLevel[];
  recentSweeps: LiquiditySweepEvent[];
  failedAuctions: FailedAuctionEvent[];
  volatilityState: VolatilityState;
  sessionState: SessionState;
  newsRisk: NewsRiskEnvironment;
  dataQualityScore: number;
  overallEnvironmentSuitability: 'FAVORABLE' | 'MODERATE_CAUTION' | 'HIGH_RISK_FILTERED' | 'PROHIBITED';
}
