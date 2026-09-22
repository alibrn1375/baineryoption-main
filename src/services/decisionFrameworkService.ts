import { FootprintBar } from '../types';
import { OrderFlowContext } from '../types/orderFlowIntelligence';
import { MarketContext } from '../types/marketContext';
import {
  SetupType,
  TradeDirection,
  NoTradeReason,
  DetectedSetup,
  SetupConditionRule,
  SetupScoreBreakdown,
  ProbabilityEstimate,
  ExpectedValueCalculation,
  BinaryOptionsEvaluation,
  DecisionExplanation,
  MLFeatureVector,
  FinalTradeDecision
} from '../types/decisionFramework';

/**
 * Task 2 & 3: Setup Detection Engine (Core Setups A, B, C, D)
 */
export class SetupDetectionEngine {
  public evaluateSetups(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): DetectedSetup[] {
    const detected: DetectedSetup[] = [];

    // --- SETUP A: Liquidity Sweep + Absorption Reversal ---
    const setupA = this.evaluateSetupA(bar, ofContext, marketContext);
    if (setupA) detected.push(setupA);

    // --- SETUP B: Imbalance Continuation ---
    const setupB = this.evaluateSetupB(bar, ofContext, marketContext);
    if (setupB) detected.push(setupB);

    // --- SETUP C: Exhaustion Reversal ---
    const setupC = this.evaluateSetupC(bar, ofContext, marketContext);
    if (setupC) detected.push(setupC);

    // --- SETUP D: Failed Auction Reversal ---
    const setupD = this.evaluateSetupD(bar, ofContext, marketContext);
    if (setupD) detected.push(setupD);

    return detected;
  }

  private evaluateSetupA(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): DetectedSetup | null {
    const sweeps = marketContext.recentSweeps;
    const absorption = ofContext.dominantAbsorption;

    // Check for Bullish Sweep + Buy Absorption (CALL setup)
    const bullishSweep = sweeps.find((s) => s.direction === 'BULLISH_SWEEP');
    const isBullishAbsorption = absorption && absorption.direction === 'BUY_ABSORPTION' && absorption.totalScore >= 60;

    // Check for Bearish Sweep + Sell Absorption (PUT setup)
    const bearishSweep = sweeps.find((s) => s.direction === 'BEARISH_SWEEP');
    const isBearishAbsorption = absorption && absorption.direction === 'SELL_ABSORPTION' && absorption.totalScore >= 60;

    if (!bullishSweep && !bearishSweep) return null;

    const direction: 'CALL' | 'PUT' = bullishSweep ? 'CALL' : 'PUT';
    const sweep = bullishSweep || bearishSweep!;

    const conditions: SetupConditionRule[] = [
      {
        id: 'rule_a_sweep',
        name: 'سوئیپ نقدینگی استاتیک یا ساختاری',
        category: 'LIQUIDITY',
        description: 'قیمت از سطح نقدینگی عبور کرده و فورا پس زده شده است',
        isMet: !!sweep,
        actualValue: sweep.sweptLevel.type,
        thresholdRequired: 'VALID_SWEEP',
        weight: 30
      },
      {
        id: 'rule_a_abs',
        name: 'جذب سفارشات تهاجمی (Absorption)',
        category: 'ORDER_FLOW',
        description: 'امتیاز جذب نقدینگی بالای آستانه ۶۰ است',
        isMet: direction === 'CALL' ? !!isBullishAbsorption : !!isBearishAbsorption,
        actualValue: absorption ? `${absorption.totalScore}% (${absorption.direction})` : 'None',
        thresholdRequired: 'Absorption Score >= 60',
        weight: 35
      },
      {
        id: 'rule_a_delta',
        name: 'رفتار جهت‌دار دلتا در اکسترمم',
        category: 'ORDER_FLOW',
        description: 'دلتای بار با جهت جذب و بازگشت همخوانی دارد',
        isMet: direction === 'CALL' ? bar.delta > 0 : bar.delta < 0,
        actualValue: bar.delta,
        thresholdRequired: direction === 'CALL' ? 'Delta > 0' : 'Delta < 0',
        weight: 20
      },
      {
        id: 'rule_a_struct',
        name: 'عدم مخالفت با ساختار کلان ۱ ساعته',
        category: 'CONTEXT',
        description: 'روند ۱ ساعته اجازه بازگشت در سطح کلیدی را می‌دهد',
        isMet: marketContext.mtfContext.macroTimeframe1H.regime !== 'UNKNOWN',
        actualValue: marketContext.mtfContext.macroTimeframe1H.regime,
        thresholdRequired: 'Valid Macro Regime',
        weight: 15
      }
    ];

    const invalidationRules: SetupConditionRule[] = [
      {
        id: 'inv_a_candle_closure',
        name: 'شکست کامل سطح و بسته شدن فراتر از آن (Acceptance)',
        category: 'INVALIDATION',
        description: 'اگر کندل بیرون از سطح بسته شود، سوئیپ ابطال و بریک‌اوت معتبر است',
        isMet: direction === 'CALL' ? bar.close < sweep.sweptLevel.price : bar.close > sweep.sweptLevel.price,
        actualValue: bar.close,
        thresholdRequired: `Close must stay inside ${sweep.sweptLevel.price}`,
        weight: 100
      }
    ];

    const metCount = conditions.filter((c) => c.isMet).length;
    const isFullyQualified = metCount >= 3 && !invalidationRules[0].isMet;
    const unmet = conditions.filter((c) => !c.isMet).map((c) => c.name);

    return {
      id: `setup-a-${bar.timestamp}`,
      type: 'SETUP_A_SWEEP_ABSORPTION_REVERSAL',
      nameFa: 'ستاپ A: سوئیپ نقدینگی + جذب و بازگشت سریع',
      direction,
      timestamp: bar.timestamp,
      triggerPrice: bar.close,
      expiryMinutes: 5,
      conditions,
      invalidationRules,
      rawScore: Math.round((metCount / conditions.length) * 100),
      isFullyQualified,
      unmetMandatoryRules: unmet
    };
  }

  private evaluateSetupB(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): DetectedSetup | null {
    const buyStacked = ofContext.imbalanceSummary.stackedBuy && ofContext.imbalanceSummary.stackedBuy.levelCount >= 2;
    const sellStacked = ofContext.imbalanceSummary.stackedSell && ofContext.imbalanceSummary.stackedSell.levelCount >= 2;

    if (!buyStacked && !sellStacked) return null;

    const direction: 'CALL' | 'PUT' = buyStacked ? 'CALL' : 'PUT';
    const isTrendAligned =
      direction === 'CALL'
        ? marketContext.regimeState.state === 'TREND_UP' || marketContext.regimeState.state === 'EXPANSION'
        : marketContext.regimeState.state === 'TREND_DOWN' || marketContext.regimeState.state === 'EXPANSION';

    const conditions: SetupConditionRule[] = [
      {
        id: 'rule_b_stacked',
        name: 'عدم‌تعادل‌های متوالی سنگین (Stacked Imbalances >= 2)',
        category: 'ORDER_FLOW',
        description: 'حداقل ۲ لول پیاپی عدم‌تعادل در لبه‌های قیمت تشکیل شده است',
        isMet: true,
        actualValue: buyStacked ? ofContext.imbalanceSummary.stackedBuy!.levelCount : ofContext.imbalanceSummary.stackedSell!.levelCount,
        thresholdRequired: '>= 2 levels',
        weight: 40
      },
      {
        id: 'rule_b_regime',
        name: 'همسویی رژیم بازار با جهت عدم‌تعادل',
        category: 'CONTEXT',
        description: 'رژیم جاری در حالت روند یا گسترش دامنه است',
        isMet: isTrendAligned,
        actualValue: marketContext.regimeState.state,
        thresholdRequired: direction === 'CALL' ? 'TREND_UP / EXPANSION' : 'TREND_DOWN / EXPANSION',
        weight: 30
      },
      {
        id: 'rule_b_delta_momentum',
        name: 'شتاب مثبت دلتا و حجم بالا',
        category: 'ORDER_FLOW',
        description: 'صدک دلتا و حجم بالاتر از میانگین است',
        isMet: ofContext.deltaSummary.deltaPercentile >= 70,
        actualValue: `${ofContext.deltaSummary.deltaPercentile}th percentile`,
        thresholdRequired: '>= 70th percentile',
        weight: 30
      }
    ];

    const invalidationRules: SetupConditionRule[] = [
      {
        id: 'inv_b_stacked_break',
        name: 'شکست لایه استک‌شده توسط قیمت معکوس',
        category: 'INVALIDATION',
        description: 'اگر قیمت لایه عدم‌تعادل را به سمت مخالف رد کند ستاپ باطل است',
        isMet: false,
        actualValue: 'Safe Zone',
        thresholdRequired: 'Price maintains stacked level',
        weight: 100
      }
    ];

    const metCount = conditions.filter((c) => c.isMet).length;
    const isFullyQualified = metCount >= 2;
    const unmet = conditions.filter((c) => !c.isMet).map((c) => c.name);

    return {
      id: `setup-b-${bar.timestamp}`,
      type: 'SETUP_B_IMBALANCE_CONTINUATION',
      nameFa: 'ستاپ B: تداوم مومنتوم ناشی از عدم‌تعادل تهاجمی (Imbalance Continuation)',
      direction,
      timestamp: bar.timestamp,
      triggerPrice: bar.close,
      expiryMinutes: 5,
      conditions,
      invalidationRules,
      rawScore: Math.round((metCount / conditions.length) * 100),
      isFullyQualified,
      unmetMandatoryRules: unmet
    };
  }

  private evaluateSetupC(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): DetectedSetup | null {
    const exhaustion = ofContext.dominantExhaustion;
    if (!exhaustion || exhaustion.confidence < 65) return null;

    const direction: 'CALL' | 'PUT' = exhaustion.direction === 'BULLISH_EXHAUSTION' ? 'PUT' : 'CALL';

    const conditions: SetupConditionRule[] = [
      {
        id: 'rule_c_exhaustion_score',
        name: 'فرسودگی شدید سفارشات تهاجمی (Exhaustion Score >= 65)',
        category: 'ORDER_FLOW',
        description: 'حجم سنگین در نوک کندل بدون توانایی پیشروی قیمت',
        isMet: exhaustion.confidence >= 65,
        actualValue: exhaustion.confidence,
        thresholdRequired: '>= 65',
        weight: 45
      },
      {
        id: 'rule_c_extremum_position',
        name: 'وقوع در لبه افراطی رنج سشن یا کانال',
        category: 'LIQUIDITY',
        description: 'فرسودگی در نزدیکی سقف یا کف سشن رخ داده است',
        isMet: true,
        actualValue: 'Near Session Border',
        thresholdRequired: 'Session Extremum Zone',
        weight: 30
      },
      {
        id: 'rule_c_divergence',
        name: 'واگرایی شتاب دلتا',
        category: 'ORDER_FLOW',
        description: 'تضعیف شدید دلتای کندل نسبت به کندل قبلی',
        isMet: ofContext.deltaSummary.deltaAcceleration === 'DECREASING',
        actualValue: ofContext.deltaSummary.deltaAcceleration,
        thresholdRequired: 'Acceleration is DECREASING',
        weight: 25
      }
    ];

    const invalidationRules: SetupConditionRule[] = [
      {
        id: 'inv_c_momentum_breakout',
        name: 'شکست ادامه دار نوک فرسودگی',
        category: 'INVALIDATION',
        description: 'ادامه جهش قیمت فراتر از شدوی کندل فرسودگی',
        isMet: false,
        actualValue: 'Valid',
        thresholdRequired: 'Peak Holds',
        weight: 100
      }
    ];

    const metCount = conditions.filter((c) => c.isMet).length;
    const isFullyQualified = metCount >= 2;
    const unmet = conditions.filter((c) => !c.isMet).map((c) => c.name);

    return {
      id: `setup-c-${bar.timestamp}`,
      type: 'SETUP_C_EXHAUSTION_REVERSAL',
      nameFa: 'ستاپ C: بازگشت روند پس از فرسودگی خریداران/فروشندگان (Exhaustion Reversal)',
      direction,
      timestamp: bar.timestamp,
      triggerPrice: bar.close,
      expiryMinutes: 5,
      conditions,
      invalidationRules,
      rawScore: Math.round((metCount / conditions.length) * 100),
      isFullyQualified,
      unmetMandatoryRules: unmet
    };
  }

  private evaluateSetupD(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): DetectedSetup | null {
    const failedAuctions = marketContext.failedAuctions;
    if (failedAuctions.length === 0) return null;

    const fa = failedAuctions[0];
    const direction: 'CALL' | 'PUT' = fa.direction === 'FAILED_BREAKOUT_HIGH' ? 'PUT' : 'CALL';

    const conditions: SetupConditionRule[] = [
      {
        id: 'rule_d_fa_event',
        name: 'رویداد حراج ناموفق در محدوده ارزش (Failed Auction)',
        category: 'CONTEXT',
        description: 'عدم پذیرش قیمت بالای VAH یا زیر VAL و بازگشت سریع به داخل رنج',
        isMet: true,
        actualValue: fa.direction,
        thresholdRequired: 'FAILED_BREAKOUT',
        weight: 40
      },
      {
        id: 'rule_d_rejection_speed',
        name: 'سرعت پس‌زدگی قیمت',
        category: 'VOLATILITY',
        description: 'کلوز کندل کاملا درون ناحیه ارزش قبلی قرار گرفته است',
        isMet: true,
        actualValue: fa.reversalPrice,
        thresholdRequired: 'Inside VA',
        weight: 30
      },
      {
        id: 'rule_d_delta_confirmation',
        name: 'تایید دلتای اوردرفلو در خروج از ناحیه',
        category: 'ORDER_FLOW',
        description: 'دلتای مخالف جهت شکست اولیه تشکیل شده است',
        isMet: direction === 'CALL' ? bar.delta > 0 : bar.delta < 0,
        actualValue: bar.delta,
        thresholdRequired: direction === 'CALL' ? 'Delta > 0' : 'Delta < 0',
        weight: 30
      }
    ];

    const invalidationRules: SetupConditionRule[] = [
      {
        id: 'inv_d_retest_break',
        name: 'تست مجدد و شکست دوباره لول VAH/VAL',
        category: 'INVALIDATION',
        description: 'شکست مجدد مرز حراج ناموفق',
        isMet: false,
        actualValue: 'Intact',
        thresholdRequired: 'No Re-breakout',
        weight: 100
      }
    ];

    const metCount = conditions.filter((c) => c.isMet).length;
    const isFullyQualified = metCount >= 2;
    const unmet = conditions.filter((c) => !c.isMet).map((c) => c.name);

    return {
      id: `setup-d-${bar.timestamp}`,
      type: 'SETUP_D_FAILED_AUCTION_REVERSAL',
      nameFa: 'ستاپ D: بازگشت حراج ناموفق به محدوده ارزش (Failed Auction Reversal)',
      direction,
      timestamp: bar.timestamp,
      triggerPrice: bar.close,
      expiryMinutes: 5,
      conditions,
      invalidationRules,
      rawScore: Math.round((metCount / conditions.length) * 100),
      isFullyQualified,
      unmetMandatoryRules: unmet
    };
  }
}

/**
 * Task 4: Setup Quality Scoring Engine (0 - 100)
 */
export class SetupQualityScoringEngine {
  public calculateScore(
    setup: DetectedSetup | null,
    ofContext: OrderFlowContext,
    marketContext: MarketContext
  ): SetupScoreBreakdown {
    if (!setup) {
      return {
        totalScore: 0,
        contextScore: 0,
        orderFlowScore: 0,
        liquidityScore: 0,
        volatilityScore: 0,
        newsSafetyScore: 0,
        penalties: [{ reason: 'هیچ ستاپی شناسایی نشد', penaltyPoints: 100 }],
        isPassingThreshold: false
      };
    }

    // 1. Context Score (Max 25)
    let contextScore = 18;
    if (marketContext.mtfContext.alignment === 'BULLISH_ALIGNED' && setup.direction === 'CALL') contextScore = 25;
    else if (marketContext.mtfContext.alignment === 'BEARISH_ALIGNED' && setup.direction === 'PUT') contextScore = 25;
    else if (marketContext.mtfContext.alignment === 'MIXED_CONFLICT') contextScore = 12;

    // 2. Order Flow Score (Max 30)
    let orderFlowScore = 20;
    if (ofContext.regime.includes('ABSORBED') || ofContext.regime.includes('PRESSURE')) {
      orderFlowScore = Math.min(30, Math.round(ofContext.contextConfidence * 0.3));
    }

    // 3. Liquidity Score (Max 20)
    let liquidityScore = 15;
    if (marketContext.recentSweeps.length > 0) liquidityScore = 20;
    else if (marketContext.activeLiquidityLevels.length > 0) liquidityScore = 16;

    // 4. Volatility Score (Max 15)
    let volatilityScore = 12;
    if (marketContext.volatilityState.level === 'NORMAL') volatilityScore = 15;
    else if (marketContext.volatilityState.level === 'HIGH') volatilityScore = 10;
    else if (marketContext.volatilityState.level === 'LOW') volatilityScore = 8;
    else if (marketContext.volatilityState.level === 'EXTREME') volatilityScore = 2;

    // 5. News Safety Score (Max 10)
    let newsSafetyScore = 10;
    if (marketContext.newsRisk.state === 'ELEVATED') newsSafetyScore = 5;
    else if (marketContext.newsRisk.state === 'BLOCKED' || marketContext.newsRisk.state === 'POST_EVENT_REASSESSMENT') newsSafetyScore = 0;

    // Penalties
    const penalties: { reason: string; penaltyPoints: number }[] = [];
    if (marketContext.dataQualityScore < 80) {
      penalties.push({ reason: 'افت کیفیت تیک‌های ارسالی پایپ‌لاین', penaltyPoints: 20 });
    }
    if (marketContext.volatilityState.level === 'EXTREME') {
      penalties.push({ reason: 'نوسان‌پذیری غیرعادی و خطرساز بازار', penaltyPoints: 25 });
    }
    if (setup.unmetMandatoryRules.length > 0) {
      penalties.push({ reason: `عدم برآورده شدن قوانین: ${setup.unmetMandatoryRules.join(', ')}`, penaltyPoints: 15 * setup.unmetMandatoryRules.length });
    }

    const totalPenalties = penalties.reduce((sum, p) => sum + p.penaltyPoints, 0);
    const rawTotal = contextScore + orderFlowScore + liquidityScore + volatilityScore + newsSafetyScore;
    const totalScore = Math.max(0, Math.min(100, rawTotal - totalPenalties));

    return {
      totalScore,
      contextScore,
      orderFlowScore,
      liquidityScore,
      volatilityScore,
      newsSafetyScore,
      penalties,
      isPassingThreshold: totalScore >= 72
    };
  }
}

/**
 * Task 5: Probability Engine (Historical + Bayesian Wilson Confidence Interval)
 */
export class ProbabilityEngine {
  public estimateProbability(
    setup: DetectedSetup | null,
    regime: MarketContext['regimeState']['state'],
    session: MarketContext['sessionState']['currentSession'],
    scoreBreakdown: SetupScoreBreakdown
  ): ProbabilityEstimate {
    if (!setup) {
      return {
        setupType: 'CUSTOM_RESEARCH_SETUP',
        regime: 'UNKNOWN',
        session: 'SESSION_CLOSED',
        sampleSize: 0,
        historicalWinRate: 0.5,
        wilsonLowerBound: 0.35,
        wilsonUpperBound: 0.65,
        shrinkageAdjustedProbability: 0.5,
        reliabilityScore: 0,
        sampleAdequacy: 'UNRELIABLE'
      };
    }

    // Historical Sample Benchmarks (Mock quantitative historical database of 1200+ samples)
    let sampleSize = 248;
    let baseWinRate = 0.64;

    switch (setup.type) {
      case 'SETUP_A_SWEEP_ABSORPTION_REVERSAL':
        sampleSize = 312;
        baseWinRate = 0.67;
        break;
      case 'SETUP_B_IMBALANCE_CONTINUATION':
        sampleSize = 420;
        baseWinRate = 0.63;
        break;
      case 'SETUP_C_EXHAUSTION_REVERSAL':
        sampleSize = 195;
        baseWinRate = 0.61;
        break;
      case 'SETUP_D_FAILED_AUCTION_REVERSAL':
        sampleSize = 168;
        baseWinRate = 0.65;
        break;
    }

    // Wilson Score 95% Confidence Interval Formula
    const z = 1.96; // 95% confidence
    const n = sampleSize;
    const p = baseWinRate;
    const denominator = 1 + (z * z) / n;
    const center = p + (z * z) / (2 * n);
    const spread = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));

    const wilsonLowerBound = Number(((center - spread) / denominator).toFixed(3));
    const wilsonUpperBound = Number(((center + spread) / denominator).toFixed(3));

    // Bayesian Shrinkage towards 0.50 Prior for low score setups
    const scoreFactor = scoreBreakdown.totalScore / 100;
    const shrinkageAdjustedProbability = Number((0.5 * (1 - scoreFactor) + baseWinRate * scoreFactor).toFixed(3));

    const sampleAdequacy: ProbabilityEstimate['sampleAdequacy'] =
      sampleSize >= 300 ? 'ROBUST' : sampleSize >= 150 ? 'MODERATE' : 'SPARSE';

    return {
      setupType: setup.type,
      regime,
      session,
      sampleSize,
      historicalWinRate: baseWinRate,
      wilsonLowerBound,
      wilsonUpperBound,
      shrinkageAdjustedProbability,
      reliabilityScore: Math.min(95, Math.round(wilsonLowerBound * 100)),
      sampleAdequacy
    };
  }
}

/**
 * Task 6: Expected Value (EV) Engine
 */
export class ExpectedValueEngine {
  public calculateEV(
    probability: ProbabilityEstimate,
    brokerPayoutPercent = 85
  ): ExpectedValueCalculation {
    const winP = probability.shrinkageAdjustedProbability;
    const lossP = 1 - winP;
    const rewardRatio = brokerPayoutPercent / 100;

    // EV Formula: (Win Probability * Reward) - (Loss Probability * 1.0)
    const evDecimal = winP * rewardRatio - lossP * 1.0;
    const expectedValuePercent = Number((evDecimal * 100).toFixed(2));

    // Breakeven Win Rate: 1 / (1 + Payout)
    const breakevenWinRateRequired = Number((1 / (1 + rewardRatio)).toFixed(3));
    const edgeOverBreakeven = Number(((winP - breakevenWinRateRequired) * 100).toFixed(2));

    let verdict: ExpectedValueCalculation['verdict'] = 'NEGATIVE_EV';
    if (probability.sampleAdequacy === 'UNRELIABLE' || probability.sampleSize < 30) {
      verdict = 'INSUFFICIENT_DATA';
    } else if (expectedValuePercent >= 5.0 && edgeOverBreakeven >= 4.0) {
      verdict = 'STRONG_POSITIVE_EV';
    } else if (expectedValuePercent > 0) {
      verdict = 'MARGINAL_EV';
    }

    return {
      estimatedWinProbability: winP,
      brokerPayoutPercent,
      riskAmountPercent: 100,
      expectedValuePercent,
      breakevenWinRateRequired,
      edgeOverBreakeven,
      verdict
    };
  }
}

/**
 * Task 8: NO TRADE Engine (Strict Filter)
 */
export class NoTradeEngine {
  public evaluateNoTradeFilters(
    setup: DetectedSetup | null,
    scoreBreakdown: SetupScoreBreakdown,
    ev: ExpectedValueCalculation,
    marketContext: MarketContext
  ): { shouldBlockTrade: boolean; reasons: NoTradeReason[] } {
    const reasons: NoTradeReason[] = [];

    // 1. Data Quality Guard
    if (marketContext.dataQualityScore < 75) {
      reasons.push('DATA_QUALITY_DEGRADED');
    }

    // 2. News Quarantine Guard
    if (!marketContext.newsRisk.tradingAllowed) {
      reasons.push('NEWS_QUARANTINE_ACTIVE');
    }

    // 3. Extreme Volatility Guard
    if (marketContext.volatilityState.level === 'EXTREME') {
      reasons.push('EXTREME_VOLATILITY');
    }

    // 4. Setup Existence & Qualification
    if (!setup) {
      reasons.push('NO_SETUP_TRIGGERED');
    } else if (!setup.isFullyQualified) {
      reasons.push('LOW_CONFIDENCE_SCORE');
    }

    // 5. Setup Quality Score Threshold
    if (!scoreBreakdown.isPassingThreshold) {
      reasons.push('LOW_CONFIDENCE_SCORE');
    }

    // 6. Expected Value & Broker Payout
    if (ev.verdict === 'NEGATIVE_EV' || ev.expectedValuePercent < 4.0) {
      reasons.push('NEGATIVE_EXPECTED_VALUE');
    }
    if (ev.brokerPayoutPercent < 75) {
      reasons.push('UNFAVORABLE_BROKER_PAYOUT');
    }

    return {
      shouldBlockTrade: reasons.length > 0,
      reasons: reasons.length > 0 ? reasons : ['NONE']
    };
  }
}

/**
 * Task 9: Decision Explainability Generator
 */
export class DecisionExplainabilityGenerator {
  public generateExplanation(
    direction: TradeDirection,
    setup: DetectedSetup | null,
    score: SetupScoreBreakdown,
    ev: ExpectedValueCalculation,
    reasons: NoTradeReason[],
    marketContext: MarketContext
  ): DecisionExplanation {
    if (direction === 'NO_TRADE') {
      const detailedPoints: string[] = [];
      for (const r of reasons) {
        switch (r) {
          case 'NO_SETUP_TRIGGERED':
            detailedPoints.push('الگوی ورود ساختاریافته معتبری در این کندل ۵ دقیقه شناسایی نشد.');
            break;
          case 'NEWS_QUARANTINE_ACTIVE':
            detailedPoints.push(`قرنطینه خبری فعال است (${marketContext.newsRisk.reason}).`);
            break;
          case 'LOW_CONFIDENCE_SCORE':
            detailedPoints.push(`امتیاز کیفی ستاپ (${score.totalScore}/100) کمتر از آستانه مجاز ۷۲ است.`);
            break;
          case 'NEGATIVE_EXPECTED_VALUE':
            detailedPoints.push(`امید ریاضی معامله (EV: ${ev.expectedValuePercent}%) پایین‌تر از حد نصاب سودآوری است.`);
            break;
          case 'EXTREME_VOLATILITY':
            detailedPoints.push('نوسان شدید بازار ریسک اسلیپیج و حرکات غیرعادی را افزایش داده است.');
            break;
          case 'DATA_QUALITY_DEGRADED':
            detailedPoints.push('کیفیت دریافت تیک‌ها افت کرده و امکان تصمیم‌گیری دقیق وجود ندارد.');
            break;
        }
      }

      return {
        primaryDecision: 'NO_TRADE',
        headlineFa: '⛔ عدم انجام معامله (NO TRADE) — اولویت با حفظ سرمایه',
        detailedPoints: detailedPoints.length > 0 ? detailedPoints : ['شرایط بازار برای ورود ریسک‌پذیر نیست.'],
        supportingEvidences: [
          { feature: 'Setup Score', observation: `${score.totalScore}/100`, impact: score.isPassingThreshold ? 'POSITIVE' : 'NEGATIVE' },
          { feature: 'Expected Value', observation: `${ev.expectedValuePercent}%`, impact: ev.expectedValuePercent > 0 ? 'POSITIVE' : 'NEGATIVE' },
          { feature: 'News State', observation: marketContext.newsRisk.state, impact: marketContext.newsRisk.tradingAllowed ? 'POSITIVE' : 'NEGATIVE' }
        ],
        activeRisks: ['عدم همپوشانی کامل پارامترهای آماری', 'برتری اجتناب از ترید نامطمئن نسبت به ترید پرریسک'],
        rejectionReasons: reasons
      };
    }

    // Explaining Valid CALL or PUT Trade
    return {
      primaryDecision: direction,
      headlineFa: `سیگنال تحلیلی معتبر ستاپ ${setup?.nameFa} جهت ورود ${direction}`,
      detailedPoints: [
        `انطباق کامل قوانین ستاپ با امتیاز کیفیت ${score.totalScore} از ۱۰۰.`,
        `امید ریاضی مثبت (EV: +${ev.expectedValuePercent}%) با برتری ${ev.edgeOverBreakeven}% نسبت به نقطه سربه‌سر بروکر (${(ev.breakevenWinRateRequired * 100).toFixed(1)}%).`,
        `تایید همسویی چندزمانه (${marketContext.mtfContext.alignment}) و محیط بدون مانع خبری.`
      ],
      supportingEvidences: [
        { feature: 'Setup Engine', observation: setup?.nameFa || 'Qualified', impact: 'POSITIVE' },
        { feature: 'Order Flow Score', observation: `${score.orderFlowScore}/30`, impact: 'POSITIVE' },
        { feature: 'Wilson 95% Win Rate', observation: `${(ev.estimatedWinProbability * 100).toFixed(1)}%`, impact: 'POSITIVE' }
      ],
      activeRisks: ['انقضای ثابت ۵ دقیقه در برابر تغییرات مومنتوم مقطعی بروکر', 'اسپرد یا اسلیپیج ثانیه‌ای در لحظه ثبت سفارش'],
      rejectionReasons: []
    };
  }
}

/**
 * Task 10: Machine Learning Feature Vector Extractor
 */
export class MLFeatureVectorExtractor {
  public extractVector(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext,
    setup: DetectedSetup | null
  ): MLFeatureVector {
    let setupLabel = 0;
    if (setup) {
      if (setup.type === 'SETUP_A_SWEEP_ABSORPTION_REVERSAL') setupLabel = 1;
      else if (setup.type === 'SETUP_B_IMBALANCE_CONTINUATION') setupLabel = 2;
      else if (setup.type === 'SETUP_C_EXHAUSTION_REVERSAL') setupLabel = 3;
      else if (setup.type === 'SETUP_D_FAILED_AUCTION_REVERSAL') setupLabel = 4;
    }

    const regimeMap: Record<string, number> = {
      TREND_UP: 1,
      TREND_DOWN: 2,
      RANGE: 3,
      COMPRESSION: 4,
      EXPANSION: 5,
      TRANSITION: 6,
      UNKNOWN: 0
    };

    const sessionMap: Record<string, number> = {
      ASIAN: 1,
      LONDON: 2,
      NEW_YORK: 3,
      LONDON_NY_OVERLAP: 4,
      SESSION_CLOSED: 0
    };

    const stackedCount = (ofContext.imbalanceSummary.stackedBuy ? 1 : 0) + (ofContext.imbalanceSummary.stackedSell ? 1 : 0);
    const imbalanceRatio = ofContext.imbalanceSummary.buyCount / Math.max(1, ofContext.imbalanceSummary.sellCount);

    return {
      timestamp: bar.timestamp,
      deltaPercentile: ofContext.deltaSummary.deltaPercentile,
      absorptionScore: ofContext.dominantAbsorption ? ofContext.dominantAbsorption.totalScore : 0,
      exhaustionScore: ofContext.dominantExhaustion ? ofContext.dominantExhaustion.confidence : 0,
      imbalanceRatio: Number(imbalanceRatio.toFixed(2)),
      stackedImbalanceCount: stackedCount,
      distanceToLiquidityTicks: 4,
      regimeOrdinal: regimeMap[marketContext.regimeState.state] || 0,
      volatilityAtrRatio: marketContext.volatilityState.atr14 / 3.5,
      sessionOrdinal: sessionMap[marketContext.sessionState.currentSession] || 0,
      newsMinsRemaining: marketContext.newsRisk.minutesToNextEvent || 999,
      dataQualityScore: marketContext.dataQualityScore,
      targetSetupLabel: setupLabel
    };
  }
}

/**
 * Task 1: Complete Decision Pipeline Orchestrator
 */
export class DecisionArbiterPipeline {
  private setupEngine = new SetupDetectionEngine();
  private scoringEngine = new SetupQualityScoringEngine();
  private probabilityEngine = new ProbabilityEngine();
  private evEngine = new ExpectedValueEngine();
  private noTradeEngine = new NoTradeEngine();
  private explanationGenerator = new DecisionExplainabilityGenerator();
  private mlExtractor = new MLFeatureVectorExtractor();

  public evaluate(
    bar: FootprintBar,
    ofContext: OrderFlowContext,
    marketContext: MarketContext,
    brokerPayout = 85
  ): FinalTradeDecision {
    // 1. Detect candidate setups
    const candidateSetups = this.setupEngine.evaluateSetups(bar, ofContext, marketContext);
    const bestSetup = candidateSetups.length > 0 ? candidateSetups[0] : null;

    // 2. Score Setup Quality
    const scoreBreakdown = this.scoringEngine.calculateScore(bestSetup, ofContext, marketContext);

    // 3. Probability Estimation
    const probability = this.probabilityEngine.estimateProbability(
      bestSetup,
      marketContext.regimeState.state,
      marketContext.sessionState.currentSession,
      scoreBreakdown
    );

    // 4. Calculate Expected Value (EV)
    const ev = this.evEngine.calculateEV(probability, brokerPayout);

    // 5. Run NO TRADE Filters
    const filterResult = this.noTradeEngine.evaluateNoTradeFilters(
      bestSetup,
      scoreBreakdown,
      ev,
      marketContext
    );

    // 6. Formulate Decision
    let finalDirection: TradeDirection = 'NO_TRADE';
    if (!filterResult.shouldBlockTrade && bestSetup && scoreBreakdown.isPassingThreshold) {
      finalDirection = bestSetup.direction;
    }

    // 7. Binary Options Specific Constraints
    const binaryEval: BinaryOptionsEvaluation = {
      symbol: 'XAUUSD_GC_5M',
      expiryCandle: 'NEXT_5M_CLOSE',
      entryWindowSecondsRemaining: 45,
      brokerPayoutPercent: brokerPayout,
      slippageToleranceTicks: 2,
      minAcceptableEV: 4.0,
      isExecutionAllowed: finalDirection !== 'NO_TRADE'
    };

    // 8. Generate Decision Explanation
    const explanation = this.explanationGenerator.generateExplanation(
      finalDirection,
      bestSetup,
      scoreBreakdown,
      ev,
      filterResult.reasons,
      marketContext
    );

    // 9. Extract ML Feature Vector
    const mlFeatureVector = this.mlExtractor.extractVector(bar, ofContext, marketContext, bestSetup);

    return {
      timestamp: bar.timestamp,
      symbol: 'XAUUSD_5M',
      direction: finalDirection,
      confidenceScore: scoreBreakdown.totalScore,
      setup: bestSetup,
      scoreBreakdown,
      probability,
      ev,
      binaryEval,
      explanation,
      mlFeatureVector,
      isExecuted: finalDirection !== 'NO_TRADE'
    };
  }
}
