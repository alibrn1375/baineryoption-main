import { FootprintBar, MarketStructure, NewsEvent } from '../types';
import { MarketRegimeType, TradingSessionType, VolatilityLevel, NewsRiskState } from './marketContext';
import { SetupType, TradeDirection, MLFeatureVector, FinalTradeDecision } from './decisionFramework';

// --- Task 2: Historical Replay Types ---
export interface ReplayEvent {
  timestamp: number;
  stepIndex: number;
  currentBar: FootprintBar;
  historicalWindow: FootprintBar[]; // Strictly bars up to t-1
  availableFeatures: MLFeatureVector;
  isDecisionBar: boolean;
}

// --- Task 3: Binary Options Simulation Types ---
export type BinaryTradeOutcome = 'WIN' | 'LOSS' | 'TIE';

export interface BinaryTradeResult {
  id: string;
  setupId: string;
  setupType: SetupType;
  direction: 'CALL' | 'PUT';
  entryTimestamp: number;
  entryTimeStr: string;
  expiryTimestamp: number;
  expiryTimeStr: string;
  entryPrice: number;
  expiryPrice: number;
  priceDelta: number;
  result: BinaryTradeOutcome;
  brokerPayoutPercent: number;
  stakeAmountUsd: number;
  profitUsd: number;
  cumulativeProfitUsd: number;
  latencySecondsApplied: number;
  slippageTicksApplied: number;
  marketRegime: MarketRegimeType;
  session: TradingSessionType;
  volatilityLevel: VolatilityLevel;
  newsState: NewsRiskState;
  score: number;
  isPaperTrade?: boolean;
}

// --- Task 4: Metrics Engine Types ---
export interface BasicPerformanceMetrics {
  totalBarsEvaluated: number;
  totalSignalsGenerated: number;
  noTradeCount: number;
  totalTradesExecuted: number;
  winCount: number;
  lossCount: number;
  tieCount: number;
  winRate: number; // e.g. 64.2%
}

export interface RiskAndDrawdownMetrics {
  maxConsecutiveWins: number;
  maxConsecutiveLosses: number;
  currentStreak: number;
  streakType: 'WIN' | 'LOSS' | 'NONE';
  maxDrawdownUsd: number;
  maxDrawdownPercent: number;
  drawdownDurationBars: number;
  profitFactor: number;
  recoveryFactor: number;
}

export interface StatisticalMetrics {
  expectedValueUsd: number;
  expectancyPercent: number;
  stdDeviationProfit: number;
  sharpeRatioEquivalent: number;
  wilsonLowerBound95: number;
  wilsonUpperBound95: number;
  sampleAdequacy: 'ROBUST' | 'MODERATE' | 'SPARSE' | 'UNRELIABLE';
  monteCarloPValue: number;
  isStatisticallySignificant: boolean;
}

export interface BinarySpecificMetrics {
  brokerPayoutPercent: number;
  breakevenWinRateRequired: number; // e.g. 54.05% for 85% payout
  edgeOverBreakeven: number; // winRate - breakevenWinRateRequired
  payoutSensitivityTable: { payout: number; breakeven: number; netProfitUsd: number; evPercent: number }[];
}

export interface BacktestPerformanceReport {
  timestamp: number;
  symbol: string;
  timeframe: string;
  basic: BasicPerformanceMetrics;
  risk: RiskAndDrawdownMetrics;
  stats: StatisticalMetrics;
  binary: BinarySpecificMetrics;
  trades: BinaryTradeResult[];
}

// --- Task 5: Setup Analytics Types ---
export interface SetupConditionPerformance {
  conditionName: string;
  winRateWhenMet: number;
  occurrences: number;
  impactScore: number;
}

export interface SetupPerformanceSummary {
  setupType: SetupType;
  nameFa: string;
  sampleSize: number;
  winCount: number;
  lossCount: number;
  winRate: number;
  expectancyPercent: number;
  wilsonLowerBound: number;
  wilsonUpperBound: number;
  sessionPerformance: Record<TradingSessionType, { trades: number; winRate: number }>;
  regimePerformance: Record<MarketRegimeType, { trades: number; winRate: number }>;
  volatilityPerformance: Record<VolatilityLevel, { trades: number; winRate: number }>;
  bestConditions: string[];
  worstConditions: string[];
  recommendation: 'DEPLOY_LIVE' | 'NEEDS_OPTIMIZATION' | 'REJECT';
}

// --- Task 6: Walk-Forward Validation Types ---
export interface WalkForwardFold {
  foldIndex: number;
  trainRange: { start: string; end: string; barsCount: number };
  validationRange: { start: string; end: string; barsCount: number };
  inSampleWinRate: number;
  outOfSampleWinRate: number;
  inSampleTrades: number;
  outOfSampleTrades: number;
  performanceDegradationPercent: number; // (OOS - IS) / IS
  isRobust: boolean;
}

export interface WalkForwardReport {
  folds: WalkForwardFold[];
  averageInSampleWinRate: number;
  averageOutOfSampleWinRate: number;
  overallDegradationPercent: number;
  overfittingIndex: number; // 0 (none) to 100 (heavily overfitted)
  robustnessVerdict: 'EXCELLENT_GENERALIZATION' | 'MODERATE_GENERALIZATION' | 'OVERFITTED';
}

// --- Task 7: Monte Carlo Analysis Types ---
export interface MonteCarloSimulationPath {
  pathIndex: number;
  finalEquityUsd: number;
  maxDrawdownUsd: number;
  maxLosingStreak: number;
}

export interface MonteCarloResult {
  simulationCount: number;
  tradesPerSimulation: number;
  medianFinalEquityUsd: number;
  percentile5thEquityUsd: number; // 95% worst-case VaR
  percentile95thEquityUsd: number; // best-case
  worstCaseDrawdownUsd: number;
  averageMaxLosingStreak: number;
  riskOfRuinPercent: number; // Probability of reaching -50% equity
  profitProbabilityPercent: number; // % of paths profitable
  paths: MonteCarloSimulationPath[];
}

// --- Task 8: Parameter Stability Analysis Types ---
export interface ParameterTestPoint {
  parameterValue: number;
  winRate: number;
  tradesCount: number;
  profitUsd: number;
  evPercent: number;
}

export interface ParameterAnalysis {
  parameterName: string;
  descriptionFa: string;
  testedRange: { min: number; max: number; step: number };
  currentValue: number;
  stableRange: { min: number; max: number };
  testPoints: ParameterTestPoint[];
  performanceVariance: number;
  isCurveFitted: boolean;
}

// --- Task 9: Research Journal Types ---
export interface ResearchRecord {
  id: string;
  timestamp: number;
  timeStr: string;
  setupType: SetupType;
  decision: TradeDirection;
  confidenceScore: number;
  featureVector: MLFeatureVector;
  decisionExplanation: string;
  tradeOutcome?: BinaryTradeOutcome;
  actualPriceDelta?: number;
  researchNotes: string;
  modelVersion: string;
}

// --- Task 11: Paper Trading Types ---
export interface ActivePaperContract {
  id: string;
  setupType: SetupType;
  direction: 'CALL' | 'PUT';
  entryTimestamp: number;
  expiryTimestamp: number;
  entryPrice: number;
  currentPrice: number;
  secondsRemaining: number;
  stakeUsd: number;
  potentialPayoutUsd: number;
  status: 'PENDING_EXPIRY' | 'SETTLING';
}

export interface PaperTradingState {
  isActive: boolean;
  virtualBalanceUsd: number;
  startingBalanceUsd: number;
  activeContracts: ActivePaperContract[];
  settledTrades: BinaryTradeResult[];
  dailyPnlUsd: number;
  dailyWinRate: number;
}

// --- Task 12: Failure Analysis Types ---
export type FailureRootCause =
  | 'MACRO_STRUCTURE_CONFLICT'
  | 'FALSE_SWEEP_ACCEPTANCE'
  | 'UNABSORBED_AGGRESSIVE_FLOW'
  | 'NEWS_SLIPPAGE_OR_SPREAD_SPIKE'
  | 'LOW_LIQUIDITY_CHOP'
  | 'LATE_MOMENTUM_ENTRY';

export interface FailureAnalysisRecord {
  tradeId: string;
  timestamp: number;
  timeStr: string;
  setupType: SetupType;
  direction: 'CALL' | 'PUT';
  entryPrice: number;
  expiryPrice: number;
  lossMagnitudeTicks: number;
  primaryRootCause: FailureRootCause;
  rootCauseDescriptionFa: string;
  mitigationRuleSuggestion: string;
  featureAnomalies: { feature: string; observed: string; expectation: string }[];
}
