import { MarketRegimeType, VolatilityLevel, TradingSessionType, NewsRiskState } from './marketContext';
import { AbsorptionFeature, ExhaustionFeature, StackedImbalanceFeature, DeltaFeature } from './orderFlowIntelligence';

export type SetupType =
  | 'SETUP_A_SWEEP_ABSORPTION_REVERSAL'
  | 'SETUP_B_IMBALANCE_CONTINUATION'
  | 'SETUP_C_EXHAUSTION_REVERSAL'
  | 'SETUP_D_FAILED_AUCTION_REVERSAL'
  | 'CUSTOM_RESEARCH_SETUP';

export type TradeDirection = 'CALL' | 'PUT' | 'NO_TRADE';

export type NoTradeReason =
  | 'NONE'
  | 'NO_SETUP_TRIGGERED'
  | 'LOW_CONFIDENCE_SCORE'
  | 'DATA_QUALITY_DEGRADED'
  | 'NEWS_QUARANTINE_ACTIVE'
  | 'EXTREME_VOLATILITY'
  | 'POOR_MULTI_TIMEFRAME_ALIGNMENT'
  | 'CONFLICTING_ORDER_FLOW'
  | 'NEGATIVE_EXPECTED_VALUE'
  | 'UNFAVORABLE_BROKER_PAYOUT'
  | 'INSUFFICIENT_HISTORICAL_SAMPLE';

export interface SetupConditionRule {
  id: string;
  name: string;
  category: 'CONTEXT' | 'ORDER_FLOW' | 'LIQUIDITY' | 'VOLATILITY' | 'INVALIDATION';
  description: string;
  isMet: boolean;
  actualValue: string | number;
  thresholdRequired: string | number;
  weight: number; // 0 - 100
}

export interface DetectedSetup {
  id: string;
  type: SetupType;
  nameFa: string;
  direction: 'CALL' | 'PUT';
  timestamp: number;
  triggerPrice: number;
  expiryMinutes: number; // typically 5m
  conditions: SetupConditionRule[];
  invalidationRules: SetupConditionRule[];
  rawScore: number; // 0 - 100
  isFullyQualified: boolean;
  unmetMandatoryRules: string[];
}

export interface SetupScoreBreakdown {
  totalScore: number; // 0 - 100
  contextScore: number; // 0 - 25
  orderFlowScore: number; // 0 - 30
  liquidityScore: number; // 0 - 20
  volatilityScore: number; // 0 - 15
  newsSafetyScore: number; // 0 - 10
  penalties: { reason: string; penaltyPoints: number }[];
  isPassingThreshold: boolean;
}

export interface ProbabilityEstimate {
  setupType: SetupType;
  regime: MarketRegimeType;
  session: TradingSessionType;
  sampleSize: number;
  historicalWinRate: number; // 0.0 - 1.0 (e.g. 0.62)
  wilsonLowerBound: number; // 95% confidence interval lower bound
  wilsonUpperBound: number;
  shrinkageAdjustedProbability: number; // Bayesian shrunk probability
  reliabilityScore: number; // 0 - 100
  sampleAdequacy: 'ROBUST' | 'MODERATE' | 'SPARSE' | 'UNRELIABLE';
}

export interface ExpectedValueCalculation {
  estimatedWinProbability: number; // 0.0 - 1.0
  brokerPayoutPercent: number; // e.g. 85 for 85% payout
  riskAmountPercent: number; // 100% of stake
  expectedValuePercent: number; // EV % of stake
  breakevenWinRateRequired: number; // 1 / (1 + payout/100)
  edgeOverBreakeven: number; // estimatedWinProbability - breakevenWinRateRequired
  verdict: 'STRONG_POSITIVE_EV' | 'MARGINAL_EV' | 'NEGATIVE_EV' | 'INSUFFICIENT_DATA';
}

export interface BinaryOptionsEvaluation {
  symbol: string;
  expiryCandle: 'CURRENT_5M_CLOSE' | 'NEXT_5M_CLOSE';
  entryWindowSecondsRemaining: number;
  brokerPayoutPercent: number;
  slippageToleranceTicks: number;
  minAcceptableEV: number; // e.g. +5%
  isExecutionAllowed: boolean;
}

export interface DecisionExplanation {
  primaryDecision: TradeDirection;
  headlineFa: string;
  detailedPoints: string[];
  supportingEvidences: { feature: string; observation: string; impact: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE' }[];
  activeRisks: string[];
  rejectionReasons: NoTradeReason[];
}

export interface MLFeatureVector {
  timestamp: number;
  deltaPercentile: number;
  absorptionScore: number;
  exhaustionScore: number;
  imbalanceRatio: number;
  stackedImbalanceCount: number;
  distanceToLiquidityTicks: number;
  regimeOrdinal: number; // 0 to 6
  volatilityAtrRatio: number;
  sessionOrdinal: number; // 0 to 4
  newsMinsRemaining: number;
  dataQualityScore: number;
  targetSetupLabel: number; // 0: None, 1: A, 2: B, 3: C, 4: D
}

export interface FinalTradeDecision {
  timestamp: number;
  symbol: string;
  direction: TradeDirection;
  confidenceScore: number;
  setup: DetectedSetup | null;
  scoreBreakdown: SetupScoreBreakdown;
  probability: ProbabilityEstimate;
  ev: ExpectedValueCalculation;
  binaryEval: BinaryOptionsEvaluation;
  explanation: DecisionExplanation;
  mlFeatureVector: MLFeatureVector;
  isExecuted: boolean;
}
