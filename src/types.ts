export type TriStateDecision = 'CALL' | 'PUT' | 'NO_TRADE';

export type AggressorSide = 'BUY' | 'SELL' | 'UNKNOWN';

export interface NormalizedTick {
  id: string;
  timestamp: number; // UTC ms
  symbol: 'GC_FUT' | 'XAUUSD_SPOT';
  price: number;
  size: number;
  aggressorSide: AggressorSide;
  bidPrice: number;
  askPrice: number;
}

export interface PriceLevelVolume {
  price: number;
  bidVolume: number;
  askVolume: number;
  totalVolume: number;
  delta: number;
  isPoc?: boolean;
  bidImbalance?: boolean; // Diagonal imbalance: bid > 3x ask of next level
  askImbalance?: boolean; // Diagonal imbalance: ask > 3x bid of previous level
  isAbsorption?: boolean; // Large passive limit absorbed aggressive volume
}

export interface FootprintBar {
  id: string;
  time: string;
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  delta: number;
  cvd: number;
  pocPrice: number;
  vah: number; // Value Area High (70% vol)
  val: number; // Value Area Low (70% vol)
  priceLevels: PriceLevelVolume[];
  unfinishedHigh: boolean;
  unfinishedLow: boolean;
  stackedBuyImbalances: number;
  stackedSellImbalances: number;
  absorptionDetected: 'BULLISH' | 'BEARISH' | 'NONE';
  deltaDivergence: 'BULLISH' | 'BEARISH' | 'NONE';
}

export interface MarketStructure {
  timeframe: '15M' | '1H';
  trend: 'BULLISH' | 'BEARISH' | 'RANGING';
  bslPrice: number; // Buy-side Liquidity (Swing High Pool)
  sslPrice: number; // Sell-side Liquidity (Swing Low Pool)
  nearestFvgTop?: number;
  nearestFvgBottom?: number;
  volatilityRegime: 'COMPRESSION' | 'NORMAL' | 'HIGH_VOLATILITY';
  atr: number;
}

export interface NewsEvent {
  id: string;
  name: string;
  scheduledTime: number; // Timestamp
  impact: 'HIGH' | 'MEDIUM' | 'LOW';
  currency: string;
  quarantineMinutesBefore: number;
  quarantineMinutesAfter: number;
  forecast?: string;
  previous?: string;
  actual?: string;
}

export interface SetupChecklistItem {
  name: string;
  satisfied: boolean;
  weight: number;
  details: string;
}

export interface SignalDecision {
  id: string;
  timestamp: number;
  timeString: string;
  action: TriStateDecision;
  confidenceScore: number; // 0 - 100
  payoutViability: boolean;
  basisSpreadOk: boolean;
  newsBlockActive: boolean;
  primaryHypothesis: string;
  checklist: SetupChecklistItem[];
  rejectionReasons: string[];
  explainability: string;
  entryPriceXau: number;
  entryPriceGc: number;
}

export interface BacktestTrade {
  id: string;
  candleTime: string;
  timestamp: number;
  direction: 'CALL' | 'PUT';
  entryPrice: number;
  expiryPrice: number;
  payoutRate: number; // e.g. 0.85 for 85%
  result: 'WIN' | 'LOSS' | 'TIE';
  profitUsd: number; // based on $100 stake
  cumulativeProfit: number;
  deltaAtEntry: number;
  setupType: string;
}

export interface BacktestSummary {
  totalCandles: number;
  totalSignals: number;
  noTradeCount: number;
  callCount: number;
  putCount: number;
  winCount: number;
  lossCount: number;
  tieCount: number;
  winRate: number; // Percentage
  breakEvenRequired: number; // Percentage
  totalProfitUsd: number;
  profitFactor: number;
  maxConsecutiveLosses: number;
  expectedValuePerTrade: number;
  monteCarloPValue: number;
  isStatisticallySignificant: boolean;
}

export interface StrategyConfig {
  imbalanceRatio: number; // default 3.0 (300%)
  minStackedImbalance: number; // default 2
  minDeltaThreshold: number; // default 150 contracts
  absorptionVolumeThreshold: number; // default 250 contracts
  minPayoutRequired: number; // default 80%
  newsQuarantineBeforeMin: number; // default 15 min
  newsQuarantineAfterMin: number; // default 20 min
  maxAllowedBasisSpread: number; // default $1.50
}
