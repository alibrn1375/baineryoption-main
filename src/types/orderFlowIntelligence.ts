import { FootprintBar, PriceLevelVolume } from '../types';

export type FeatureDirection = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

export interface DeltaFeature {
  timestamp: number;
  symbol: string;
  absoluteDelta: number;
  relativeDelta: number; // Delta as % of Volume
  deltaPercentile: number; // 0 - 100 relative to recent lookback
  deltaAcceleration: 'INCREASING' | 'DECREASING' | 'STABLE';
  deltaPersistenceBars: number; // Consecutive bars with same delta direction
  divergenceCandidate: 'BULLISH_DIVERGENCE_PREP' | 'BEARISH_DIVERGENCE_PREP' | 'NONE';
  confidence: number; // 0 - 100
}

export interface ImbalanceFeature {
  price: number;
  direction: 'BUY_IMBALANCE' | 'SELL_IMBALANCE';
  ratio: number;
  aggressiveVolume: number;
  oppositeVolume: number;
  volumeDiff: number;
}

export interface StackedImbalanceFeature {
  direction: 'BUY_STACKED' | 'SELL_STACKED';
  levelCount: number;
  startPrice: number;
  endPrice: number;
  totalAggressiveVolume: number;
  stackStrength: number; // 0 - 100
  timestamp: number;
}

export interface AbsorptionFeature {
  timestamp: number;
  locationPrice: number;
  direction: 'BUY_ABSORPTION' | 'SELL_ABSORPTION';
  aggressiveVolume: number;
  priceProgressTicks: number;
  efficiencyRatio: number; // Range / Volume
  reactionTicks: number;
  volumeComponentScore: number;
  priceFailureScore: number;
  reactionScore: number;
  locationScore: number;
  deltaScore: number;
  totalScore: number; // 0 - 100
  confidence: number; // 0 - 100
}

export interface ExhaustionFeature {
  timestamp: number;
  locationPrice: number;
  direction: 'BULLISH_EXHAUSTION' | 'BEARISH_EXHAUSTION';
  extremeDelta: number;
  extremeVolume: number;
  efficiencyDropRatio: number;
  failedContinuation: boolean;
  confidence: number; // 0 - 100
}

export interface OrderFlowContext {
  timestamp: number;
  symbol: string;
  regime: 'BUY_PRESSURE' | 'SELL_PRESSURE' | 'BUY_ABSORBED' | 'SELL_ABSORBED' | 'SELL_PRESSURE_ABSORBED' | 'BUY_PRESSURE_ABSORBED' | 'EXHAUSTION_REVERSAL_RISK' | 'BALANCED_AUCTION';
  deltaSummary: DeltaFeature;
  imbalanceSummary: {
    buyCount: number;
    sellCount: number;
    stackedBuy?: StackedImbalanceFeature;
    stackedSell?: StackedImbalanceFeature;
  };
  dominantAbsorption?: AbsorptionFeature;
  dominantExhaustion?: ExhaustionFeature;
  contextConfidence: number; // 0 - 100
}

export interface AbsorptionScoringWeights {
  volumeWeight: number;       // default 0.30
  priceFailureWeight: number; // default 0.25
  reactionWeight: number;     // default 0.20
  locationWeight: number;     // default 0.15
  deltaWeight: number;        // default 0.10
}

export interface OrderFlowFeatureConfig {
  imbalanceRatio: number;          // e.g. 3.0
  minImbalanceVolume: number;      // e.g. 40 contracts
  minImbalanceDiff: number;        // e.g. 25 contracts
  minStackSize: number;            // e.g. 3 levels
  maxStackGapsAllowed: number;     // e.g. 0 levels
  absorptionVolumeThreshold: number; // e.g. 200 contracts
  absorptionMaxProgressTicks: number; // e.g. 3 ticks (1.5$)
  absorptionWeights: AbsorptionScoringWeights;
  exhaustionPercentileCutoff: number; // e.g. 90th percentile
}
