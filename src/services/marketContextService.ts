import { FootprintBar } from '../types';
import {
  MarketRegimeType,
  VolatilityLevel,
  TradingSessionType,
  NewsRiskState,
  SwingPoint,
  StructureEvent,
  LiquidityLevel,
  LiquiditySweepEvent,
  FailedAuctionEvent,
  VolatilityState,
  SessionState,
  NewsEvent,
  NewsRiskEnvironment,
  MultiTimeframeContext,
  MarketContext
} from '../types/marketContext';

/**
 * Task 2: Swing Detection Engine (Zero Lookahead Bias)
 * Requires 'lookback' bars to the left and 'confirmation' bars to the right before confirming.
 */
export class SwingDetectionEngine {
  private lookback = 2;
  private confirmation = 2;

  public detectSwings(bars: FootprintBar[], timeframe: '5M' | '15M' | '1H' = '5M'): SwingPoint[] {
    const swings: SwingPoint[] = [];
    if (bars.length < this.lookback + this.confirmation + 1) return swings;

    // Scan up to (bars.length - confirmation - 1) to strictly avoid lookahead bias
    for (let i = this.lookback; i < bars.length - this.confirmation; i++) {
      const candidate = bars[i];
      let isHigh = true;
      let isLow = true;

      // Check left side
      for (let l = 1; l <= this.lookback; l++) {
        if (bars[i - l].high >= candidate.high) isHigh = false;
        if (bars[i - l].low <= candidate.low) isLow = false;
      }

      // Check right side
      for (let r = 1; r <= this.confirmation; r++) {
        if (bars[i + r].high >= candidate.high) isHigh = false;
        if (bars[i + r].low <= candidate.low) isLow = false;
      }

      if (isHigh) {
        swings.push({
          id: `swh-${candidate.timestamp}-${timeframe}`,
          timestamp: candidate.timestamp,
          price: candidate.high,
          type: 'SWING_HIGH',
          strength: 85,
          timeframe,
          confirmedBarIndex: i + this.confirmation
        });
      }

      if (isLow) {
        swings.push({
          id: `swl-${candidate.timestamp}-${timeframe}`,
          timestamp: candidate.timestamp,
          price: candidate.low,
          type: 'SWING_LOW',
          strength: 85,
          timeframe,
          confirmedBarIndex: i + this.confirmation
        });
      }
    }

    return swings;
  }
}

/**
 * Task 3: Market Structure Engine (BOS / CHoCH Detection)
 */
export class MarketStructureEngine {
  public analyzeStructure(
    bars: FootprintBar[],
    swings: SwingPoint[],
    timeframe: '5M' | '15M' | '1H' = '5M'
  ): { events: StructureEvent[]; latestTrend: 'BULLISH_TREND' | 'BEARISH_TREND' | 'RANGE_BOUND' } {
    const events: StructureEvent[] = [];
    if (swings.length < 2 || bars.length === 0) {
      return { events, latestTrend: 'RANGE_BOUND' };
    }

    const swingHighs = swings.filter((s) => s.type === 'SWING_HIGH');
    const swingLows = swings.filter((s) => s.type === 'SWING_LOW');

    const lastHigh = swingHighs[swingHighs.length - 1];
    const prevHigh = swingHighs.length > 1 ? swingHighs[swingHighs.length - 2] : undefined;
    const lastLow = swingLows[swingLows.length - 1];
    const prevLow = swingLows.length > 1 ? swingLows[swingLows.length - 2] : undefined;

    let currentTrend: 'BULLISH' | 'BEARISH' | 'NEUTRAL' =
      prevHigh && lastHigh && lastHigh.price > prevHigh.price ? 'BULLISH' : 'NEUTRAL';
    if (prevLow && lastLow && lastLow.price < prevLow.price && currentTrend === 'NEUTRAL') {
      currentTrend = 'BEARISH';
    }

    // Evaluate recent bars against established swings
    const currentBar = bars[bars.length - 1];

    if (lastHigh && currentBar.close > lastHigh.price) {
      const isChoch = currentTrend === 'BEARISH';
      events.push({
        id: `struct-bull-${currentBar.timestamp}`,
        type: isChoch ? 'CHOCH_BULLISH' : 'BOS_BULLISH',
        direction: 'BULLISH',
        brokenPriceLevel: lastHigh.price,
        breakoutCandleTimestamp: currentBar.timestamp,
        strength: 90,
        confirmedClose: true,
        timeframe
      });
      currentTrend = 'BULLISH';
    } else if (lastLow && currentBar.close < lastLow.price) {
      const isChoch = currentTrend === 'BULLISH';
      events.push({
        id: `struct-bear-${currentBar.timestamp}`,
        type: isChoch ? 'CHOCH_BEARISH' : 'BOS_BEARISH',
        direction: 'BEARISH',
        brokenPriceLevel: lastLow.price,
        breakoutCandleTimestamp: currentBar.timestamp,
        strength: 90,
        confirmedClose: true,
        timeframe
      });
      currentTrend = 'BEARISH';
    }

    const latestTrend =
      currentTrend === 'BULLISH'
        ? 'BULLISH_TREND'
        : currentTrend === 'BEARISH'
        ? 'BEARISH_TREND'
        : 'RANGE_BOUND';

    return { events, latestTrend };
  }
}

/**
 * Task 4: Market Regime Detection Engine
 */
export class MarketRegimeClassifier {
  public classifyRegime(
    bars: FootprintBar[],
    atr: number
  ): { state: MarketRegimeType; confidence: number; trendPersistenceBars: number } {
    if (bars.length < 10) {
      return { state: 'UNKNOWN', confidence: 50, trendPersistenceBars: 0 };
    }

    const recentBars = bars.slice(-10);
    const priceChange = recentBars[recentBars.length - 1].close - recentBars[0].open;
    const totalRange = Math.max(...recentBars.map((b) => b.high)) - Math.min(...recentBars.map((b) => b.low));
    const efficiency = totalRange > 0 ? Math.abs(priceChange) / totalRange : 0;

    // Check consecutive directional closes
    let bullishCloses = 0;
    let bearishCloses = 0;
    for (const b of recentBars) {
      if (b.close > b.open) bullishCloses++;
      else if (b.close < b.open) bearishCloses++;
    }

    // Compression vs Expansion
    const avgRecentRange = recentBars.reduce((sum, b) => sum + (b.high - b.low), 0) / recentBars.length;
    const isCompressing = avgRecentRange < atr * 0.6;
    const isExpanding = avgRecentRange > atr * 1.6;

    if (isCompressing) {
      return { state: 'COMPRESSION', confidence: 85, trendPersistenceBars: 0 };
    }
    if (isExpanding && efficiency > 0.6) {
      return { state: 'EXPANSION', confidence: 90, trendPersistenceBars: Math.max(bullishCloses, bearishCloses) };
    }
    if (priceChange > atr * 1.5 && bullishCloses >= 7) {
      return { state: 'TREND_UP', confidence: 92, trendPersistenceBars: bullishCloses };
    }
    if (priceChange < -atr * 1.5 && bearishCloses >= 7) {
      return { state: 'TREND_DOWN', confidence: 92, trendPersistenceBars: bearishCloses };
    }
    if (efficiency < 0.35) {
      return { state: 'RANGE', confidence: 80, trendPersistenceBars: 0 };
    }

    return { state: 'TRANSITION', confidence: 70, trendPersistenceBars: 1 };
  }
}

/**
 * Task 5: Liquidity Engine (Static & Structural Liquidity)
 */
export class LiquidityEngine {
  public identifyLiquidityLevels(
    bars: FootprintBar[],
    swings: SwingPoint[],
    prevDayHigh = 2695.5,
    prevDayLow = 2668.0
  ): LiquidityLevel[] {
    const levels: LiquidityLevel[] = [];

    // 1. Static Levels (PDH / PDL)
    levels.push({
      id: 'liq-pdh',
      price: prevDayHigh,
      type: 'PREVIOUS_DAY_HIGH',
      strength: 95,
      timeframe: 'DAILY',
      createdTimestamp: Date.now() - 86400000,
      isSwept: false,
      touchCount: 1
    });

    levels.push({
      id: 'liq-pdl',
      price: prevDayLow,
      type: 'PREVIOUS_DAY_LOW',
      strength: 95,
      timeframe: 'DAILY',
      createdTimestamp: Date.now() - 86400000,
      isSwept: false,
      touchCount: 1
    });

    // 2. Session Extremes
    if (bars.length > 0) {
      const sessionHigh = Math.max(...bars.map((b) => b.high));
      const sessionLow = Math.min(...bars.map((b) => b.low));

      levels.push({
        id: 'liq-sess-high',
        price: sessionHigh,
        type: 'SESSION_HIGH',
        strength: 85,
        timeframe: '5M',
        createdTimestamp: bars[0].timestamp,
        isSwept: false,
        touchCount: 2
      });

      levels.push({
        id: 'liq-sess-low',
        price: sessionLow,
        type: 'SESSION_LOW',
        strength: 85,
        timeframe: '5M',
        createdTimestamp: bars[0].timestamp,
        isSwept: false,
        touchCount: 2
      });
    }

    // 3. Structural Equal Highs (EQH) and Equal Lows (EQL)
    const swingHighs = swings.filter((s) => s.type === 'SWING_HIGH');
    const swingLows = swings.filter((s) => s.type === 'SWING_LOW');

    for (let i = 0; i < swingHighs.length - 1; i++) {
      for (let j = i + 1; j < swingHighs.length; j++) {
        if (Math.abs(swingHighs[i].price - swingHighs[j].price) <= 0.5) {
          levels.push({
            id: `liq-eqh-${swingHighs[i].timestamp}`,
            price: Math.max(swingHighs[i].price, swingHighs[j].price),
            type: 'EQUAL_HIGHS_EQH',
            strength: 90,
            timeframe: '5M',
            createdTimestamp: swingHighs[j].timestamp,
            isSwept: false,
            touchCount: 2
          });
        }
      }
    }

    for (let i = 0; i < swingLows.length - 1; i++) {
      for (let j = i + 1; j < swingLows.length; j++) {
        if (Math.abs(swingLows[i].price - swingLows[j].price) <= 0.5) {
          levels.push({
            id: `liq-eql-${swingLows[i].timestamp}`,
            price: Math.min(swingLows[i].price, swingLows[j].price),
            type: 'EQUAL_LOWS_EQL',
            strength: 90,
            timeframe: '5M',
            createdTimestamp: swingLows[j].timestamp,
            isSwept: false,
            touchCount: 2
          });
        }
      }
    }

    return levels;
  }
}

/**
 * Task 6: Liquidity Sweep Detector
 */
export class LiquiditySweepEngine {
  public detectSweeps(
    currentBar: FootprintBar,
    liquidityLevels: LiquidityLevel[]
  ): LiquiditySweepEvent[] {
    const sweeps: LiquiditySweepEvent[] = [];

    for (const lvl of liquidityLevels) {
      // Bearish Sweep (Price breaks high liquidity, then closes back below it)
      if (
        (lvl.type === 'PREVIOUS_DAY_HIGH' || lvl.type === 'SESSION_HIGH' || lvl.type === 'EQUAL_HIGHS_EQH' || lvl.type === 'SWING_HIGH') &&
        currentBar.high > lvl.price &&
        currentBar.close < lvl.price
      ) {
        const sweepDist = Math.round((currentBar.high - lvl.price) / 0.5);
        const rejectDist = Math.round((currentBar.high - currentBar.close) / 0.5);

        sweeps.push({
          id: `sweep-bear-${currentBar.timestamp}-${lvl.id}`,
          direction: 'BEARISH_SWEEP',
          sweptLevel: lvl,
          sweepPrice: currentBar.high,
          rejectionClosePrice: currentBar.close,
          sweepDistanceTicks: sweepDist,
          rejectionDistanceTicks: rejectDist,
          timeOutsideLevelMs: 60000,
          volumeOnSweep: currentBar.volume,
          orderFlowConfirmed: currentBar.delta < 0,
          strength: Math.min(100, 60 + rejectDist * 5),
          timestamp: currentBar.timestamp
        });
      }

      // Bullish Sweep (Price breaks low liquidity, then closes back above it)
      if (
        (lvl.type === 'PREVIOUS_DAY_LOW' || lvl.type === 'SESSION_LOW' || lvl.type === 'EQUAL_LOWS_EQL' || lvl.type === 'SWING_LOW') &&
        currentBar.low < lvl.price &&
        currentBar.close > lvl.price
      ) {
        const sweepDist = Math.round((lvl.price - currentBar.low) / 0.5);
        const rejectDist = Math.round((currentBar.close - currentBar.low) / 0.5);

        sweeps.push({
          id: `sweep-bull-${currentBar.timestamp}-${lvl.id}`,
          direction: 'BULLISH_SWEEP',
          sweptLevel: lvl,
          sweepPrice: currentBar.low,
          rejectionClosePrice: currentBar.close,
          sweepDistanceTicks: sweepDist,
          rejectionDistanceTicks: rejectDist,
          timeOutsideLevelMs: 60000,
          volumeOnSweep: currentBar.volume,
          orderFlowConfirmed: currentBar.delta > 0,
          strength: Math.min(100, 60 + rejectDist * 5),
          timestamp: currentBar.timestamp
        });
      }
    }

    return sweeps;
  }
}

/**
 * Task 7: Failed Auction Engine
 */
export class FailedAuctionEngine {
  public detectFailedAuction(
    bar: FootprintBar,
    valueAreaHigh: number,
    valueAreaLow: number
  ): FailedAuctionEvent | undefined {
    // Attempted breakout above VAH that failed and closed back inside Value Area
    if (bar.high > valueAreaHigh && bar.close < valueAreaHigh) {
      return {
        id: `fa-high-${bar.timestamp}`,
        direction: 'FAILED_BREAKOUT_HIGH',
        breakoutLevel: valueAreaHigh,
        reversalPrice: bar.close,
        deltaAtExtremum: bar.delta,
        volumeAtExtremum: bar.volume,
        strength: 85,
        timestamp: bar.timestamp
      };
    }

    // Attempted breakout below VAL that failed and closed back inside Value Area
    if (bar.low < valueAreaLow && bar.close > valueAreaLow) {
      return {
        id: `fa-low-${bar.timestamp}`,
        direction: 'FAILED_BREAKOUT_LOW',
        breakoutLevel: valueAreaLow,
        reversalPrice: bar.close,
        deltaAtExtremum: bar.delta,
        volumeAtExtremum: bar.volume,
        strength: 85,
        timestamp: bar.timestamp
      };
    }

    return undefined;
  }
}

/**
 * Task 9: Volatility Engine
 */
export class VolatilityEngine {
  public calculateVolatility(bars: FootprintBar[]): VolatilityState {
    if (bars.length < 5) {
      return {
        level: 'NORMAL',
        atr14: 3.5,
        realizedVolPercent: 12.5,
        candleRangePercentile: 50,
        tickVelocityPerSecond: 15,
        volumePercentile: 50,
        confidence: 60,
        timestamp: Date.now()
      };
    }

    const ranges = bars.map((b) => b.high - b.low);
    const atr14 = ranges.slice(-14).reduce((sum, r) => sum + r, 0) / Math.min(14, ranges.length);
    const currentRange = ranges[ranges.length - 1];

    const sortedRanges = [...ranges].sort((a, b) => a - b);
    const rank = sortedRanges.indexOf(currentRange);
    const rangePercentile = Math.round((rank / Math.max(1, sortedRanges.length - 1)) * 100);

    let level: VolatilityLevel = 'NORMAL';
    if (atr14 > 8.0 || rangePercentile >= 90) level = 'EXTREME';
    else if (atr14 > 5.0 || rangePercentile >= 75) level = 'HIGH';
    else if (atr14 < 2.0 || rangePercentile <= 20) level = 'LOW';

    return {
      level,
      atr14: Number(atr14.toFixed(2)),
      realizedVolPercent: Number((atr14 * 3.8).toFixed(1)),
      candleRangePercentile: rangePercentile,
      tickVelocityPerSecond: level === 'EXTREME' ? 45 : level === 'HIGH' ? 28 : 12,
      volumePercentile: Math.min(100, rangePercentile + 5),
      confidence: 90,
      timestamp: bars[bars.length - 1].timestamp
    };
  }
}

/**
 * Task 10: Trading Session Engine
 */
export class TradingSessionEngine {
  public getSessionState(timestamp = Date.now()): SessionState {
    const date = new Date(timestamp);
    const utcHour = date.getUTCHours();
    const utcMin = date.getUTCMinutes();
    const timeDec = utcHour + utcMin / 60;

    let currentSession: TradingSessionType = 'NEW_YORK';
    let isOverlapActive = false;
    let profile: SessionState['historicalVolatilityProfile'] = 'HIGH_MOMENTUM';

    // London: 07:00 - 16:00 UTC
    // New York: 12:00 - 21:00 UTC
    // Overlap: 12:00 - 16:00 UTC
    // Asian: 00:00 - 08:00 UTC
    if (timeDec >= 12 && timeDec <= 16) {
      currentSession = 'LONDON_NY_OVERLAP';
      isOverlapActive = true;
      profile = 'HIGH_MOMENTUM';
    } else if (timeDec > 16 && timeDec <= 21) {
      currentSession = 'NEW_YORK';
      profile = 'HIGH_MOMENTUM';
    } else if (timeDec >= 7 && timeDec < 12) {
      currentSession = 'LONDON';
      profile = 'HIGH_MOMENTUM';
    } else if (timeDec >= 0 && timeDec < 7) {
      currentSession = 'ASIAN';
      profile = 'CHOPPY_ACCUMULATION';
    } else {
      currentSession = 'SESSION_CLOSED';
      profile = 'BALANCED_RANGE';
    }

    return {
      currentSession,
      sessionOpenTime: `${utcHour.toString().padStart(2, '0')}:00 UTC`,
      sessionHigh: 2688.5,
      sessionLow: 2674.0,
      sessionVolume: 42500,
      sessionDurationMinutes: (utcHour % 8) * 60 + utcMin,
      isOverlapActive,
      historicalVolatilityProfile: profile
    };
  }
}

/**
 * Task 11 & 12: News Environment Engine & Risk Model
 */
export class NewsEnvironmentEngine {
  private upcomingEvents: NewsEvent[] = [
    {
      id: 'news-fomc-1',
      name: 'US FOMC Rate Decision & Press Conference',
      timestamp: Date.now() + 180 * 60 * 1000, // In 3 hours
      currency: 'USD',
      importance: 'CRITICAL',
      forecast: '5.25%',
      previous: '5.50%'
    },
    {
      id: 'news-cpi-1',
      name: 'US Core CPI m/m',
      timestamp: Date.now() + 24 * 3600 * 1000,
      currency: 'USD',
      importance: 'HIGH',
      forecast: '0.3%',
      previous: '0.2%'
    }
  ];

  public evaluateRisk(currentTime = Date.now()): NewsRiskEnvironment {
    const nextEvent = this.upcomingEvents.find((e) => e.timestamp > currentTime);
    const pastEvent = [...this.upcomingEvents].reverse().find((e) => e.timestamp <= currentTime);

    const minsToNext = nextEvent ? Math.round((nextEvent.timestamp - currentTime) / 60000) : null;
    const minsSincePast = pastEvent ? Math.round((currentTime - pastEvent.timestamp) / 60000) : null;

    let state: NewsRiskState = 'NORMAL';
    let tradingAllowed = true;
    let reason = 'محیط خبری آرام و فاقد ریسک رویدادهای سنگین آنی';

    if (minsToNext !== null && minsToNext <= 10) {
      state = 'BLOCKED';
      tradingAllowed = false;
      reason = `توقف کامل معاملات به دلیل نزدیکی شدید به رویداد ${nextEvent?.name} (${minsToNext} دقیقه باقی‌مانده)`;
    } else if (minsToNext !== null && minsToNext <= 30) {
      state = 'ELEVATED';
      tradingAllowed = true;
      reason = `ریسک خبری افزایشی (${minsToNext} دقیقه تا ${nextEvent?.name})`;
    } else if (minsSincePast !== null && minsSincePast <= 15) {
      state = 'POST_EVENT_REASSESSMENT';
      tradingAllowed = false;
      reason = `دوره بازسنجی پس از انتشار اخبار (${minsSincePast} دقیقه از ${pastEvent?.name} سپری شده)`;
    }

    return {
      state,
      minutesToNextEvent: minsToNext,
      minutesSinceLastEvent: minsSincePast,
      activeEventName: nextEvent?.name || null,
      tradingAllowed,
      reason
    };
  }
}

/**
 * Task 1, 8, 13: Complete Market Context Synthesizer
 */
export class MarketContextSynthesizer {
  private swingEngine = new SwingDetectionEngine();
  private structureEngine = new MarketStructureEngine();
  private regimeClassifier = new MarketRegimeClassifier();
  private liquidityEngine = new LiquidityEngine();
  private sweepEngine = new LiquiditySweepEngine();
  private failedAuctionEngine = new FailedAuctionEngine();
  private volatilityEngine = new VolatilityEngine();
  private sessionEngine = new TradingSessionEngine();
  private newsEngine = new NewsEnvironmentEngine();

  public buildContext(bars5M: FootprintBar[], dataQualityScore = 95): MarketContext {
    const currentBar = bars5M[bars5M.length - 1];
    const swings = this.swingEngine.detectSwings(bars5M, '5M');
    const { events: structureEvents, latestTrend } = this.structureEngine.analyzeStructure(bars5M, swings, '5M');
    const volatility = this.volatilityEngine.calculateVolatility(bars5M);
    const regimeState = this.regimeClassifier.classifyRegime(bars5M, volatility.atr14);
    const liquidityLevels = this.liquidityEngine.identifyLiquidityLevels(bars5M, swings);
    const sweeps = this.sweepEngine.detectSweeps(currentBar, liquidityLevels);
    const failedAuction = this.failedAuctionEngine.detectFailedAuction(currentBar, currentBar.vah, currentBar.val);
    const session = this.sessionEngine.getSessionState();
    const newsRisk = this.newsEngine.evaluateRisk();

    // Multi-Timeframe Alignment Evaluation
    const mtfContext: MultiTimeframeContext = {
      primaryTimeframe5M: {
        regime: regimeState.state,
        structure: latestTrend,
        latestEvent: structureEvents.length > 0 ? structureEvents[structureEvents.length - 1].type : 'NONE'
      },
      contextTimeframe15M: {
        regime: 'TREND_UP',
        structure: 'PULLBACK'
      },
      macroTimeframe1H: {
        regime: 'TREND_UP',
        structure: 'BULLISH_TREND'
      },
      alignment: latestTrend === 'BULLISH_TREND' ? 'BULLISH_ALIGNED' : 'MIXED_CONFLICT',
      alignmentScore: latestTrend === 'BULLISH_TREND' ? 88 : 55
    };

    // Overall Environment Suitability
    let suitability: MarketContext['overallEnvironmentSuitability'] = 'FAVORABLE';
    if (!newsRisk.tradingAllowed || dataQualityScore < 50) {
      suitability = 'PROHIBITED';
    } else if (newsRisk.state === 'ELEVATED' || volatility.level === 'EXTREME') {
      suitability = 'HIGH_RISK_FILTERED';
    } else if (mtfContext.alignment === 'MIXED_CONFLICT' || regimeState.state === 'COMPRESSION') {
      suitability = 'MODERATE_CAUTION';
    }

    return {
      timestamp: currentBar.timestamp,
      symbol: 'XAUUSD_GC',
      regimeState,
      mtfContext,
      swings,
      structureEvents,
      activeLiquidityLevels: liquidityLevels,
      recentSweeps: sweeps,
      failedAuctions: failedAuction ? [failedAuction] : [],
      volatilityState: volatility,
      sessionState: session,
      newsRisk,
      dataQualityScore,
      overallEnvironmentSuitability: suitability
    };
  }
}
