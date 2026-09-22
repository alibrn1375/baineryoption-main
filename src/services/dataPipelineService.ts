import { TickEntity, TradeSide, DataQualityReport, QualityState, DeltaEngineState } from '../types/dataPipeline';
import { FootprintBar, PriceLevelVolume } from '../types';

/**
 * Task 3: Trade Classification with Lee-Ready algorithm fallback
 */
export function classifyTradeSide(
  price: number,
  bid: number,
  ask: number,
  previousPrice?: number
): { side: TradeSide; method: 'DIRECT_FLAG' | 'LEE_READY' | 'UNKNOWN_NEUTRAL' } {
  // 1. Exact quote match
  if (ask > bid) {
    if (price >= ask) {
      return { side: 'BUY', method: 'DIRECT_FLAG' };
    }
    if (price <= bid) {
      return { side: 'SELL', method: 'DIRECT_FLAG' };
    }
  }

  // 2. Lee-Ready Tick Rule fallback if inside spread
  if (previousPrice !== undefined && previousPrice > 0) {
    if (price > previousPrice) {
      return { side: 'BUY', method: 'LEE_READY' };
    }
    if (price < previousPrice) {
      return { side: 'SELL', method: 'LEE_READY' };
    }
  }

  // 3. Unknown Neutral: Does not contribute to directional Delta to prevent distortion
  return { side: 'UNKNOWN', method: 'UNKNOWN_NEUTRAL' };
}

/**
 * Task 4: Data Quality & Anomaly Detection Engine
 */
export class DataQualityEngine {
  private lastTimestamp = 0;
  private seenTickIds = new Set<string>();
  private missingCount = 0;
  private duplicateCount = 0;
  private outOfOrderCount = 0;
  private invalidCount = 0;

  public validateTick(
    tick: TickEntity,
    spotRefPrice?: number
  ): { isValid: boolean; report: DataQualityReport } {
    const reasons: string[] = [];
    let deduction = 0;

    // 1. Deduplication
    if (this.seenTickIds.has(tick.id)) {
      this.duplicateCount++;
      reasons.push(`تیک تکراری (Duplicate) با شناسه ${tick.id}`);
      deduction += 20;
    } else {
      this.seenTickIds.add(tick.id);
      if (this.seenTickIds.size > 5000) {
        // prune cache
        this.seenTickIds.clear();
      }
    }

    // 2. Out of order timestamps
    if (this.lastTimestamp > 0 && tick.timestamp < this.lastTimestamp) {
      this.outOfOrderCount++;
      reasons.push(`ترتیب زمانی معکوس (Out of order): تاخیر ${this.lastTimestamp - tick.timestamp}ms`);
      deduction += 25;
    } else {
      this.lastTimestamp = tick.timestamp;
    }

    // 3. Price & Volume validity
    if (tick.price <= 0 || isNaN(tick.price) || tick.price > 10000 || tick.price < 500) {
      this.invalidCount++;
      reasons.push(`قیمت نامعتبر: ${tick.price}`);
      deduction += 50;
    }
    if (tick.size <= 0 || !Number.isInteger(tick.size) || tick.size > 50000) {
      this.invalidCount++;
      reasons.push(`حجم نامعتبر: ${tick.size}`);
      deduction += 30;
    }

    // 4. Spread and Sync checks
    if (tick.bid > 0 && tick.ask > 0 && tick.bid > tick.ask) {
      reasons.push(`اسپرد منفی غیرمنطقی: Bid(${tick.bid}) > Ask(${tick.ask})`);
      deduction += 40;
    }

    // 5. GC vs Spot Basis Sync
    let syncOffset = 0;
    if (spotRefPrice && spotRefPrice > 0) {
      syncOffset = Math.abs(tick.price - spotRefPrice);
      if (syncOffset > 5.0) {
        reasons.push(`ناهماهنگی شدید اختلاف قیمت فیوچرز GC با اسپات XAUUSD (${syncOffset.toFixed(2)}$)`);
        deduction += 35;
      }
    }

    const score = Math.max(0, 100 - deduction);
    let state: QualityState = 'GOOD';
    let shouldHalt = false;

    if (score < 50 || deduction >= 50) {
      state = 'INVALID';
      shouldHalt = true;
    } else if (score < 80) {
      state = 'DEGRADED';
    }

    const report: DataQualityReport = {
      timestamp: tick.timestamp,
      score,
      state,
      missingTicksDetected: this.missingCount,
      duplicateTicksDropped: this.duplicateCount,
      outOfOrderFixed: this.outOfOrderCount,
      invalidVolumeCount: this.invalidCount,
      invalidPriceCount: this.invalidCount,
      feedDelayMs: Math.max(0, Date.now() - tick.timestamp),
      syncOffsetMs: syncOffset,
      reasons,
      shouldHaltProcessing: shouldHalt
    };

    return { isValid: state !== 'INVALID', report };
  }

  public reset() {
    this.lastTimestamp = 0;
    this.seenTickIds.clear();
    this.missingCount = 0;
    this.duplicateCount = 0;
    this.outOfOrderCount = 0;
    this.invalidCount = 0;
  }
}

/**
 * Task 5, 6, 7: Pure Microsecond Footprint & Delta/CVD Engine
 */
export class FootprintEngine {
  private currentBar: FootprintBar | null = null;
  private levelMap = new Map<number, { bid: number; ask: number; total: number; delta: number }>();
  private tickStep = 0.5; // Gold futures price bucket (0.50$ per level)
  private sessionCvd = 0;
  private swingCvd = 0;
  private lastBarEndTimestamp = 0;
  private barDurationMs = 5 * 60 * 1000; // 5M

  public processTick(tick: TickEntity): { barCompleted: FootprintBar | null; activeBar: FootprintBar } {
    const bucketPrice = Math.round(tick.price / this.tickStep) * this.tickStep;

    // Check if new 5M bar period started
    let completedBar: FootprintBar | null = null;
    const barEnd = this.currentBar ? this.currentBar.timestamp + this.barDurationMs : 0;
    if (!this.currentBar || tick.timestamp >= barEnd) {
      if (this.currentBar) {
        completedBar = this.finalizeBar(this.currentBar);
      }
      this.currentBar = this.createNewBar(tick.timestamp, tick.price);
    }

    // Update OHLC
    this.currentBar.high = Math.max(this.currentBar.high, tick.price);
    this.currentBar.low = Math.min(this.currentBar.low, tick.price);
    this.currentBar.close = tick.price;
    this.currentBar.volume += tick.size;

    // Update Price Level Ladder
    const existing = this.levelMap.get(bucketPrice) || { bid: 0, ask: 0, total: 0, delta: 0 };
    existing.total += tick.size;

    if (tick.side === 'BUY') {
      existing.ask += tick.size;
      existing.delta += tick.size;
      this.currentBar.delta += tick.size;
      this.sessionCvd += tick.size;
      this.swingCvd += tick.size;
    } else if (tick.side === 'SELL') {
      existing.bid += tick.size;
      existing.delta -= tick.size;
      this.currentBar.delta -= tick.size;
      this.sessionCvd -= tick.size;
      this.swingCvd -= tick.size;
    }
    // Note: UNKNOWN trades add to volume but not Bid/Ask to preserve mathematical Delta purity

    this.levelMap.set(bucketPrice, existing);
    this.currentBar.cvd = this.sessionCvd;

    // Refresh levels list & POC
    this.updateLevelsAndPoc(this.currentBar);

    return { barCompleted: completedBar, activeBar: this.currentBar };
  }

  private createNewBar(timestamp: number, price: number): FootprintBar {
    const barStart = Math.floor(timestamp / this.barDurationMs) * this.barDurationMs;

    this.levelMap.clear();

    return {
      id: `bar-${barStart}`,
      time: new Date(barStart).toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }),
      timestamp: barStart,
      open: price,
      high: price,
      low: price,
      close: price,
      volume: 0,
      delta: 0,
      cvd: this.sessionCvd,
      pocPrice: price,
      vah: price,
      val: price,
      priceLevels: [],
      unfinishedHigh: false,
      unfinishedLow: false,
      stackedBuyImbalances: 0,
      stackedSellImbalances: 0,
      absorptionDetected: 'NONE',
      deltaDivergence: 'NONE'
    };
  }

  private updateLevelsAndPoc(bar: FootprintBar) {
    const levels: PriceLevelVolume[] = [];
    let maxVol = 0;
    let poc = bar.open;

    const sortedPrices = Array.from(this.levelMap.keys()).sort((a, b) => b - a);

    for (const p of sortedPrices) {
      const d = this.levelMap.get(p)!;
      if (d.total > maxVol) {
        maxVol = d.total;
        poc = p;
      }
      levels.push({
        price: p,
        bidVolume: d.bid,
        askVolume: d.ask,
        totalVolume: d.total,
        delta: d.delta,
        isPoc: false,
        bidImbalance: false,
        askImbalance: false
      });
    }

    // Set POC flag
    for (const lvl of levels) {
      if (lvl.price === poc) {
        lvl.isPoc = true;
      }
    }

    bar.pocPrice = poc;
    bar.priceLevels = levels;
  }

  private finalizeBar(bar: FootprintBar): FootprintBar {
    // Calculate diagonal imbalances (Task 5)
    const levels = [...bar.priceLevels].sort((a, b) => a.price - b.price);
    let stackedBuys = 0;
    let stackedSells = 0;
    let maxStackedBuys = 0;
    let maxStackedSells = 0;

    for (let i = 0; i < levels.length; i++) {
      const current = levels[i];
      
      // Buy imbalance: Ask at level i vs Bid at level i-1 (diagonal)
      if (i > 0) {
        const lowerBid = levels[i - 1].bidVolume;
        if (current.askVolume >= lowerBid * 3.0 && current.askVolume >= 40) {
          current.askImbalance = true;
          stackedBuys++;
          maxStackedBuys = Math.max(maxStackedBuys, stackedBuys);
        } else {
          stackedBuys = 0;
        }
      }

      // Sell imbalance: Bid at level i vs Ask at level i+1 (diagonal)
      if (i < levels.length - 1) {
        const higherAsk = levels[i + 1].askVolume;
        if (current.bidVolume >= higherAsk * 3.0 && current.bidVolume >= 40) {
          current.bidImbalance = true;
          stackedSells++;
          maxStackedSells = Math.max(maxStackedSells, stackedSells);
        } else {
          stackedSells = 0;
        }
      }
    }

    bar.stackedBuyImbalances = maxStackedBuys;
    bar.stackedSellImbalances = maxStackedSells;

    // Detect absorption at extremes
    const lowest = levels[0];
    const highest = levels[levels.length - 1];
    const avgVol = bar.volume / Math.max(1, levels.length);

    if (lowest && lowest.bidVolume >= avgVol * 2.5) {
      bar.absorptionDetected = 'BULLISH';
    } else if (highest && highest.askVolume >= avgVol * 2.5) {
      bar.absorptionDetected = 'BEARISH';
    }

    return { ...bar, priceLevels: levels.sort((a, b) => b.price - a.price) };
  }

  public resetSessionCvd() {
    this.sessionCvd = 0;
  }

  public resetSwingCvd() {
    this.swingCvd = 0;
  }

  public getDeltaEngineState(): DeltaEngineState {
    return {
      candleDelta: this.currentBar?.delta || 0,
      rollingDelta5m: this.currentBar?.delta || 0,
      sessionDelta: this.sessionCvd,
      swingDelta: this.swingCvd,
      sessionCvd: this.sessionCvd,
      rollingCvd5m: this.sessionCvd,
      swingCvd: this.swingCvd,
      lastResetTimestamp: this.lastBarEndTimestamp
    };
  }
}
