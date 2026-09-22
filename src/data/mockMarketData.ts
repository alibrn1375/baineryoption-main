import { FootprintBar, MarketStructure, NormalizedTick, PriceLevelVolume } from '../types';

export function generatePriceLevels(
  low: number,
  high: number,
  close: number,
  open: number,
  deltaBias: 'BULLISH' | 'BEARISH' | 'NEUTRAL',
  hasAbsorption: boolean,
  hasStackedImbalance: boolean
): { levels: PriceLevelVolume[]; poc: number; vah: number; val: number; delta: number; volume: number } {
  const step = 0.5; // Gold tick step e.g. 0.50
  const levels: PriceLevelVolume[] = [];
  let current = Math.round(low * 2) / 2;
  const max = Math.round(high * 2) / 2;

  let totalVol = 0;
  let totalDelta = 0;
  let maxLevelVol = 0;
  let pocPrice = current;

  while (current <= max + 0.001) {
    const distFromCenter = Math.abs(current - (low + high) / 2);
    const centerWeight = Math.max(0.3, 1 - distFromCenter / (Math.max(1, high - low) * 0.8));
    
    // Base volume
    const levelTotal = Math.round((Math.random() * 200 + 100) * centerWeight * 2);
    
    let bidRatio = 0.5;
    if (deltaBias === 'BULLISH') {
      bidRatio = 0.35 + Math.random() * 0.2; // more ask
    } else if (deltaBias === 'BEARISH') {
      bidRatio = 0.55 + Math.random() * 0.25; // more bid
    } else {
      bidRatio = 0.45 + Math.random() * 0.1;
    }

    let bidVol = Math.round(levelTotal * bidRatio);
    let askVol = levelTotal - bidVol;

    // Absorption injection at extremes
    let isAbsorption = false;
    if (hasAbsorption) {
      if (deltaBias === 'BULLISH' && Math.abs(current - low) <= 0.5) {
        // Sellers attacked market (huge bid volume sold into limit buy) but price stopped falling
        bidVol = Math.round(bidVol * 2.8);
        isAbsorption = true;
      } else if (deltaBias === 'BEARISH' && Math.abs(current - high) <= 0.5) {
        // Buyers attacked market (huge ask volume bought into limit sell) but price stopped rising
        askVol = Math.round(askVol * 2.8);
        isAbsorption = true;
      }
    }

    const lvlDelta = askVol - bidVol;
    totalVol += (bidVol + askVol);
    totalDelta += lvlDelta;

    if (bidVol + askVol > maxLevelVol) {
      maxLevelVol = bidVol + askVol;
      pocPrice = current;
    }

    levels.push({
      price: Number(current.toFixed(1)),
      bidVolume: bidVol,
      askVolume: askVol,
      totalVolume: bidVol + askVol,
      delta: lvlDelta,
      isAbsorption,
    });

    current = Number((current + step).toFixed(1));
  }

  // Calculate Diagonal Imbalances (comparing ask at P to bid at P-1, and bid at P to ask at P+1)
  for (let i = 0; i < levels.length; i++) {
    levels[i].isPoc = (levels[i].price === pocPrice);
    
    // Diagonal Ask Imbalance (Aggressive Buyer: Ask(i) > 3 * Bid(i-1))
    if (i > 0 && levels[i].askVolume >= levels[i - 1].bidVolume * 3 && levels[i].askVolume > 50) {
      levels[i].askImbalance = true;
    }
    // Diagonal Bid Imbalance (Aggressive Seller: Bid(i) > 3 * Ask(i+1))
    if (i < levels.length - 1 && levels[i].bidVolume >= levels[i + 1].askVolume * 3 && levels[i].bidVolume > 50) {
      levels[i].bidImbalance = true;
    }
  }

  // Force stacked imbalance if requested
  if (hasStackedImbalance) {
    if (deltaBias === 'BULLISH') {
      for (let i = Math.max(0, levels.length - 3); i < levels.length; i++) {
        levels[i].askImbalance = true;
        levels[i].askVolume = Math.round(levels[i].askVolume * 2);
      }
    } else if (deltaBias === 'BEARISH') {
      for (let i = 0; i < Math.min(3, levels.length); i++) {
        levels[i].bidImbalance = true;
        levels[i].bidVolume = Math.round(levels[i].bidVolume * 2);
      }
    }
  }

  // Value Area (70% of total volume around POC)
  const sortedByVol = [...levels].sort((a, b) => b.totalVolume - a.totalVolume);
  let accumulated = 0;
  const target70 = totalVol * 0.7;
  const vaLevels: number[] = [];
  for (const lvl of sortedByVol) {
    accumulated += lvl.totalVolume;
    vaLevels.push(lvl.price);
    if (accumulated >= target70) break;
  }

  const vah = Math.max(...vaLevels, pocPrice);
  const val = Math.min(...vaLevels, pocPrice);

  return { levels, poc: pocPrice, vah, val, delta: totalDelta, volume: totalVol };
}

// Generate realistic sequence of historical 5M footprint bars for Gold (around $2650.0)
export function createHistoricalFootprintBars(): FootprintBar[] {
  const basePrices = [
    { o: 2646.0, h: 2649.5, l: 2644.5, c: 2648.5, bias: 'BULLISH' as const, abs: false, imb: true, time: '13:00' },
    { o: 2648.5, h: 2652.0, l: 2647.0, c: 2651.0, bias: 'BULLISH' as const, abs: false, imb: true, time: '13:05' },
    { o: 2651.0, h: 2654.5, l: 2650.0, c: 2653.5, bias: 'BULLISH' as const, abs: false, imb: false, time: '13:10' },
    { o: 2653.5, h: 2656.0, l: 2651.5, c: 2652.0, bias: 'BEARISH' as const, abs: true, imb: true, time: '13:15' }, // Absorption at 2656 High
    { o: 2652.0, h: 2653.0, l: 2647.5, c: 2648.0, bias: 'BEARISH' as const, abs: false, imb: true, time: '13:20' },
    { o: 2648.0, h: 2649.5, l: 2643.0, c: 2644.0, bias: 'BEARISH' as const, abs: false, imb: false, time: '13:25' },
    { o: 2644.0, h: 2646.0, l: 2640.5, c: 2642.0, bias: 'BEARISH' as const, abs: true, imb: false, time: '13:30' }, // Sweep of SSL 2641
    { o: 2642.0, h: 2647.0, l: 2641.5, c: 2646.5, bias: 'BULLISH' as const, abs: true, imb: true, time: '13:35' }, // Active Reversal Setup (CALL)
  ];

  let runningCvd = 450;
  const bars: FootprintBar[] = [];

  basePrices.forEach((bp, index) => {
    const { levels, poc, vah, val, delta, volume } = generatePriceLevels(
      bp.l,
      bp.h,
      bp.c,
      bp.o,
      bp.bias,
      bp.abs,
      bp.imb
    );

    runningCvd += delta;

    const stackedBuys = levels.filter(l => l.askImbalance).length;
    const stackedSells = levels.filter(l => l.bidImbalance).length;

    let absorptionDetected: 'BULLISH' | 'BEARISH' | 'NONE' = 'NONE';
    if (bp.abs && bp.bias === 'BULLISH') absorptionDetected = 'BULLISH';
    if (bp.abs && bp.bias === 'BEARISH') absorptionDetected = 'BEARISH';

    let deltaDivergence: 'BULLISH' | 'BEARISH' | 'NONE' = 'NONE';
    // Bar made lower low but delta is positive -> Bullish divergence
    if (index > 0 && bp.l < basePrices[index - 1].l && delta > 0) {
      deltaDivergence = 'BULLISH';
    } else if (index > 0 && bp.h > basePrices[index - 1].h && delta < 0) {
      deltaDivergence = 'BEARISH';
    }

    bars.push({
      id: `bar-${index + 1}`,
      time: bp.time,
      timestamp: Date.now() - (basePrices.length - index) * 5 * 60 * 1000,
      open: bp.o,
      high: bp.h,
      low: bp.l,
      close: bp.c,
      volume,
      delta,
      cvd: runningCvd,
      pocPrice: poc,
      vah,
      val,
      priceLevels: levels,
      unfinishedHigh: index === 3 ? true : false,
      unfinishedLow: false,
      stackedBuyImbalances: stackedBuys,
      stackedSellImbalances: stackedSells,
      absorptionDetected,
      deltaDivergence,
    });
  });

  return bars;
}

export const mockMarketStructure15M: MarketStructure = {
  timeframe: '15M',
  trend: 'BEARISH',
  bslPrice: 2656.5,
  sslPrice: 2640.5,
  nearestFvgTop: 2653.0,
  nearestFvgBottom: 2649.5,
  volatilityRegime: 'NORMAL',
  atr: 3.8,
};

export const mockMarketStructure1H: MarketStructure = {
  timeframe: '1H',
  trend: 'BULLISH',
  bslPrice: 2668.0,
  sslPrice: 2635.0,
  volatilityRegime: 'NORMAL',
  atr: 8.4,
};

export function generateLiveTickStream(lastPrice: number): NormalizedTick {
  const isBuy = Math.random() > 0.48;
  const spread = 0.2;
  const deltaMove = (Math.random() - 0.5) * 0.3;
  const newPrice = Number((lastPrice + deltaMove).toFixed(1));
  const size = Math.floor(Math.random() * 18) + 1;

  return {
    id: `tick-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
    timestamp: Date.now(),
    symbol: 'GC_FUT',
    price: newPrice,
    size,
    aggressorSide: isBuy ? 'BUY' : 'SELL',
    bidPrice: Number((newPrice - spread / 2).toFixed(1)),
    askPrice: Number((newPrice + spread / 2).toFixed(1)),
  };
}
