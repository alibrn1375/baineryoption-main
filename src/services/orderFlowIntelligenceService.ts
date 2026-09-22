import { FootprintBar, PriceLevelVolume } from '../types';
import {
  DeltaFeature,
  ImbalanceFeature,
  StackedImbalanceFeature,
  AbsorptionFeature,
  ExhaustionFeature,
  OrderFlowContext,
  OrderFlowFeatureConfig
} from '../types/orderFlowIntelligence';

export const defaultConfig: OrderFlowFeatureConfig = {
  imbalanceRatio: 3.0,
  minImbalanceVolume: 40,
  minImbalanceDiff: 25,
  minStackSize: 2,
  maxStackGapsAllowed: 0,
  absorptionVolumeThreshold: 200,
  absorptionMaxProgressTicks: 3,
  absorptionWeights: {
    volumeWeight: 0.30,
    priceFailureWeight: 0.25,
    reactionWeight: 0.20,
    locationWeight: 0.15,
    deltaWeight: 0.10
  },
  exhaustionPercentileCutoff: 85
};

/**
 * Task 2: Advanced Delta Intelligence Engine
 */
export class DeltaIntelligenceEngine {
  private deltaHistory: number[] = [];

  public analyzeBarDelta(
    bar: FootprintBar,
    previousBars: FootprintBar[]
  ): DeltaFeature {
    const absDelta = Math.abs(bar.delta);
    const relDelta = bar.volume > 0 ? (bar.delta / bar.volume) * 100 : 0;

    // Track delta history for percentiles
    this.deltaHistory.push(absDelta);
    if (this.deltaHistory.length > 100) this.deltaHistory.shift();

    // Percentile calculation
    const sorted = [...this.deltaHistory].sort((a, b) => a - b);
    const rank = sorted.indexOf(absDelta);
    const percentile = sorted.length > 1 ? (rank / (sorted.length - 1)) * 100 : 50;

    // Acceleration
    let acceleration: 'INCREASING' | 'DECREASING' | 'STABLE' = 'STABLE';
    if (previousBars.length >= 2) {
      const prev1Delta = Math.abs(previousBars[previousBars.length - 1].delta);
      const prev2Delta = Math.abs(previousBars[previousBars.length - 2].delta);
      if (absDelta > prev1Delta && prev1Delta > prev2Delta) {
        acceleration = 'INCREASING';
      } else if (absDelta < prev1Delta && prev1Delta < prev2Delta) {
        acceleration = 'DECREASING';
      }
    }

    // Persistence (consecutive bars with same sign)
    let persistence = 1;
    const currentSign = Math.sign(bar.delta);
    if (currentSign !== 0) {
      for (let i = previousBars.length - 1; i >= 0; i--) {
        if (Math.sign(previousBars[i].delta) === currentSign) {
          persistence++;
        } else {
          break;
        }
      }
    }

    // Divergence Preparation Detection (Higher High Price with Lower High Delta, or vice versa)
    let divergenceCandidate: 'BULLISH_DIVERGENCE_PREP' | 'BEARISH_DIVERGENCE_PREP' | 'NONE' = 'NONE';
    if (previousBars.length >= 2) {
      const prevBar = previousBars[previousBars.length - 1];
      // Price higher high, but bar delta lower
      if (bar.high > prevBar.high && bar.delta < prevBar.delta && bar.delta < 0) {
        divergenceCandidate = 'BEARISH_DIVERGENCE_PREP';
      }
      // Price lower low, but bar delta higher
      else if (bar.low < prevBar.low && bar.delta > prevBar.delta && bar.delta > 0) {
        divergenceCandidate = 'BULLISH_DIVERGENCE_PREP';
      }
    }

    const confidence = Math.min(100, Math.round(percentile * 0.6 + persistence * 10));

    return {
      timestamp: bar.timestamp,
      symbol: 'GC_FUT',
      absoluteDelta: bar.delta,
      relativeDelta: Number(relDelta.toFixed(2)),
      deltaPercentile: Number(percentile.toFixed(1)),
      deltaAcceleration: acceleration,
      deltaPersistenceBars: persistence,
      divergenceCandidate,
      confidence
    };
  }
}

/**
 * Task 3 & 4: Imbalance & Stacked Imbalance Engine
 */
export class ImbalanceEngine {
  public detectImbalances(
    bar: FootprintBar,
    config: OrderFlowFeatureConfig = defaultConfig
  ): {
    imbalances: ImbalanceFeature[];
    stackedBuys?: StackedImbalanceFeature;
    stackedSells?: StackedImbalanceFeature;
  } {
    const levels = [...bar.priceLevels].sort((a, b) => a.price - b.price);
    const imbalances: ImbalanceFeature[] = [];

    for (let i = 0; i < levels.length; i++) {
      const current = levels[i];

      // Buy Imbalance: Ask at level i vs Bid at level i-1
      if (i > 0) {
        const lowerBid = levels[i - 1].bidVolume;
        const askVol = current.askVolume;
        if (
          askVol >= lowerBid * config.imbalanceRatio &&
          askVol >= config.minImbalanceVolume &&
          askVol - lowerBid >= config.minImbalanceDiff
        ) {
          imbalances.push({
            price: current.price,
            direction: 'BUY_IMBALANCE',
            ratio: lowerBid > 0 ? Number((askVol / lowerBid).toFixed(2)) : askVol,
            aggressiveVolume: askVol,
            oppositeVolume: lowerBid,
            volumeDiff: askVol - lowerBid
          });
        }
      }

      // Sell Imbalance: Bid at level i vs Ask at level i+1
      if (i < levels.length - 1) {
        const higherAsk = levels[i + 1].askVolume;
        const bidVol = current.bidVolume;
        if (
          bidVol >= higherAsk * config.imbalanceRatio &&
          bidVol >= config.minImbalanceVolume &&
          bidVol - higherAsk >= config.minImbalanceDiff
        ) {
          imbalances.push({
            price: current.price,
            direction: 'SELL_IMBALANCE',
            ratio: higherAsk > 0 ? Number((bidVol / higherAsk).toFixed(2)) : bidVol,
            aggressiveVolume: bidVol,
            oppositeVolume: higherAsk,
            volumeDiff: bidVol - higherAsk
          });
        }
      }
    }

    // Stacked Imbalance Detection
    const buyImbalances = imbalances.filter((imb) => imb.direction === 'BUY_IMBALANCE');
    const sellImbalances = imbalances.filter((imb) => imb.direction === 'SELL_IMBALANCE');

    const stackedBuys = this.findMaxStack(buyImbalances, 'BUY_STACKED', bar.timestamp, config);
    const stackedSells = this.findMaxStack(sellImbalances, 'SELL_STACKED', bar.timestamp, config);

    return { imbalances, stackedBuys, stackedSells };
  }

  private findMaxStack(
    imbalances: ImbalanceFeature[],
    direction: 'BUY_STACKED' | 'SELL_STACKED',
    timestamp: number,
    config: OrderFlowFeatureConfig
  ): StackedImbalanceFeature | undefined {
    if (imbalances.length < config.minStackSize) return undefined;

    const sortedPrices = imbalances.map((i) => i.price).sort((a, b) => a - b);
    let currentStack: number[] = [sortedPrices[0]];
    let maxStack: number[] = [sortedPrices[0]];

    for (let i = 1; i < sortedPrices.length; i++) {
      const prevPrice = currentStack[currentStack.length - 1];
      const diff = sortedPrices[i] - prevPrice;

      // Assuming tick size 0.50
      if (Math.abs(diff - 0.5) < 0.01) {
        currentStack.push(sortedPrices[i]);
        if (currentStack.length > maxStack.length) {
          maxStack = [...currentStack];
        }
      } else {
        currentStack = [sortedPrices[i]];
      }
    }

    if (maxStack.length >= config.minStackSize) {
      const stackImbs = imbalances.filter((i) => maxStack.includes(i.price));
      const totalVol = stackImbs.reduce((acc, curr) => acc + curr.aggressiveVolume, 0);
      const strength = Math.min(100, Math.round(maxStack.length * 20 + (totalVol / 100) * 10));

      return {
        direction,
        levelCount: maxStack.length,
        startPrice: maxStack[0],
        endPrice: maxStack[maxStack.length - 1],
        totalAggressiveVolume: totalVol,
        stackStrength: strength,
        timestamp
      };
    }

    return undefined;
  }
}

/**
 * Task 5 & 6: Quantitative Absorption Engine with 5-Component Scoring
 */
export class AbsorptionEngine {
  public detectAbsorption(
    bar: FootprintBar,
    bSLPrice: number,
    sSLPrice: number,
    config: OrderFlowFeatureConfig = defaultConfig
  ): AbsorptionFeature | undefined {
    const rangeTicks = Math.max(1, Math.round((bar.high - bar.low) / 0.5));
    const efficiencyRatio = Number((rangeTicks / Math.max(1, bar.volume)).toFixed(4));
    const w = config.absorptionWeights;

    // Check Bullish Absorption (Heavy selling at low without downward progress)
    const lowestLevel = bar.priceLevels.length > 0 ? bar.priceLevels[bar.priceLevels.length - 1] : null;
    const highestLevel = bar.priceLevels.length > 0 ? bar.priceLevels[0] : null;

    let bestFeature: AbsorptionFeature | undefined = undefined;

    // 1. Bullish Absorption Evaluation
    if (lowestLevel && lowestLevel.bidVolume >= config.absorptionVolumeThreshold) {
      const volScore = Math.min(100, (lowestLevel.bidVolume / config.absorptionVolumeThreshold) * 70);
      const priceFailScore = Math.max(0, 100 - (rangeTicks / config.absorptionMaxProgressTicks) * 30);
      const reactionScore = bar.close > lowestLevel.price ? Math.min(100, Math.round((bar.close - lowestLevel.price) * 40)) : 20;
      const locationScore = Math.abs(bar.low - sSLPrice) <= 1.5 ? 100 : 50; // Near SSL pool
      const deltaScore = bar.delta > 0 ? 90 : 40; // Absorption converting to positive delta

      const totalScore = Math.round(
        volScore * w.volumeWeight +
        priceFailScore * w.priceFailureWeight +
        reactionScore * w.reactionWeight +
        locationScore * w.locationWeight +
        deltaScore * w.deltaWeight
      );

      if (totalScore >= 60) {
        bestFeature = {
          timestamp: bar.timestamp,
          locationPrice: lowestLevel.price,
          direction: 'BUY_ABSORPTION',
          aggressiveVolume: lowestLevel.bidVolume,
          priceProgressTicks: rangeTicks,
          efficiencyRatio,
          reactionTicks: Math.round((bar.close - lowestLevel.price) / 0.5),
          volumeComponentScore: Math.round(volScore),
          priceFailureScore: Math.round(priceFailScore),
          reactionScore: Math.round(reactionScore),
          locationScore: Math.round(locationScore),
          deltaScore: Math.round(deltaScore),
          totalScore,
          confidence: Math.min(100, Math.round(totalScore * 0.95))
        };
      }
    }

    // 2. Bearish Absorption Evaluation
    if (highestLevel && highestLevel.askVolume >= config.absorptionVolumeThreshold) {
      const volScore = Math.min(100, (highestLevel.askVolume / config.absorptionVolumeThreshold) * 70);
      const priceFailScore = Math.max(0, 100 - (rangeTicks / config.absorptionMaxProgressTicks) * 30);
      const reactionScore = highestLevel.price > bar.close ? Math.min(100, Math.round((highestLevel.price - bar.close) * 40)) : 20;
      const locationScore = Math.abs(bar.high - bSLPrice) <= 1.5 ? 100 : 50; // Near BSL pool
      const deltaScore = bar.delta < 0 ? 90 : 40;

      const totalScore = Math.round(
        volScore * w.volumeWeight +
        priceFailScore * w.priceFailureWeight +
        reactionScore * w.reactionWeight +
        locationScore * w.locationWeight +
        deltaScore * w.deltaWeight
      );

      if (totalScore >= 60 && (!bestFeature || totalScore > bestFeature.totalScore)) {
        bestFeature = {
          timestamp: bar.timestamp,
          locationPrice: highestLevel.price,
          direction: 'SELL_ABSORPTION',
          aggressiveVolume: highestLevel.askVolume,
          priceProgressTicks: rangeTicks,
          efficiencyRatio,
          reactionTicks: Math.round((highestLevel.price - bar.close) / 0.5),
          volumeComponentScore: Math.round(volScore),
          priceFailureScore: Math.round(priceFailScore),
          reactionScore: Math.round(reactionScore),
          locationScore: Math.round(locationScore),
          deltaScore: Math.round(deltaScore),
          totalScore,
          confidence: Math.min(100, Math.round(totalScore * 0.95))
        };
      }
    }

    return bestFeature;
  }
}

/**
 * Task 7: Exhaustion Engine
 */
export class ExhaustionEngine {
  public detectExhaustion(
    bar: FootprintBar,
    deltaFeature: DeltaFeature
  ): ExhaustionFeature | undefined {
    // Extreme delta/volume but price closed near open or failed continuation
    const isExtremeDelta = deltaFeature.deltaPercentile >= 85;
    const bodySize = Math.abs(bar.close - bar.open);
    const wicksSize = (bar.high - bar.low) - bodySize;

    if (isExtremeDelta && wicksSize > bodySize) {
      const direction = bar.delta > 0 ? 'BULLISH_EXHAUSTION' : 'BEARISH_EXHAUSTION';
      const strength = Math.min(100, Math.round(deltaFeature.deltaPercentile * 0.9 + (wicksSize / (bodySize + 0.1)) * 10));

      return {
        timestamp: bar.timestamp,
        locationPrice: bar.close,
        direction,
        extremeDelta: bar.delta,
        extremeVolume: bar.volume,
        efficiencyDropRatio: Number((bodySize / Math.max(0.1, wicksSize)).toFixed(2)),
        failedContinuation: true,
        confidence: strength
      };
    }

    return undefined;
  }
}

/**
 * Task 8: Order Flow Context Synthesizer
 */
export class OrderFlowContextBuilder {
  public synthesizeContext(
    bar: FootprintBar,
    delta: DeltaFeature,
    imbalances: { buyCount: number; sellCount: number; stackedBuy?: StackedImbalanceFeature; stackedSell?: StackedImbalanceFeature },
    absorption?: AbsorptionFeature,
    exhaustion?: ExhaustionFeature
  ): OrderFlowContext {
    let regime: OrderFlowContext['regime'] = 'BALANCED_AUCTION';
    let confidence = 50;

    if (absorption) {
      regime = absorption.direction === 'BUY_ABSORPTION' ? 'SELL_PRESSURE_ABSORBED' : 'BUY_PRESSURE_ABSORBED';
      confidence = absorption.confidence;
    } else if (exhaustion) {
      regime = 'EXHAUSTION_REVERSAL_RISK';
      confidence = exhaustion.confidence;
    } else if (imbalances.stackedBuy) {
      regime = 'BUY_PRESSURE';
      confidence = imbalances.stackedBuy.stackStrength;
    } else if (imbalances.stackedSell) {
      regime = 'SELL_PRESSURE_ABSORBED';
      confidence = imbalances.stackedSell.stackStrength;
    }

    return {
      timestamp: bar.timestamp,
      symbol: 'GC_FUT',
      regime,
      deltaSummary: delta,
      imbalanceSummary: imbalances,
      dominantAbsorption: absorption,
      dominantExhaustion: exhaustion,
      contextConfidence: confidence
    };
  }
}
