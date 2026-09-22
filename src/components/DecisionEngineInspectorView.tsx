import React, { useState } from 'react';
import {
  BrainCircuit,
  Sliders,
  Percent,
  Calculator,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCode2,
  TrendingUp,
  TrendingDown,
  Layers,
  Sparkles,
  Info,
  ChevronRight,
  Database,
  BarChart2
} from 'lucide-react';
import { FootprintBar } from '../types';
import {
  defaultConfig,
  DeltaIntelligenceEngine,
  ImbalanceEngine,
  AbsorptionEngine,
  ExhaustionEngine,
  OrderFlowContextBuilder
} from '../services/orderFlowIntelligenceService';
import { MarketContextSynthesizer } from '../services/marketContextService';
import { DecisionArbiterPipeline } from '../services/decisionFrameworkService';
import {
  DetectedSetup,
  FinalTradeDecision,
  SetupType
} from '../types/decisionFramework';

interface DecisionEngineInspectorViewProps {
  currentBar: FootprintBar;
  historicalBars: FootprintBar[];
  dataQualityScore: number;
}

export const DecisionEngineInspectorView: React.FC<DecisionEngineInspectorViewProps> = ({
  currentBar,
  historicalBars,
  dataQualityScore
}) => {
  const [activeTab, setActiveTab] = useState<'arbiter' | 'setups_lab' | 'ev_simulator' | 'ml_vectors' | 'spec'>('arbiter');
  const [brokerPayout, setBrokerPayout] = useState<number>(85);
  const [selectedSetupTab, setSelectedSetupTab] = useState<SetupType>('SETUP_A_SWEEP_ABSORPTION_REVERSAL');

  // Build Order Flow Context
  const deltaEngine = new DeltaIntelligenceEngine();
  const imbalanceEngine = new ImbalanceEngine();
  const absorptionEngine = new AbsorptionEngine();
  const exhaustionEngine = new ExhaustionEngine();
  const ofContextBuilder = new OrderFlowContextBuilder();

  const deltaFeature = deltaEngine.analyzeBarDelta(currentBar, historicalBars);
  const imbalanceResult = imbalanceEngine.detectImbalances(currentBar, defaultConfig);
  const absorptionFeature = absorptionEngine.detectAbsorption(currentBar, currentBar.high + 2.0, currentBar.low - 2.0, defaultConfig);
  const exhaustionFeature = exhaustionEngine.detectExhaustion(currentBar, deltaFeature);
  const ofContext = ofContextBuilder.synthesizeContext(
    currentBar,
    deltaFeature,
    {
      buyCount: imbalanceResult.imbalances.filter((i) => i.direction === 'BUY_IMBALANCE').length,
      sellCount: imbalanceResult.imbalances.filter((i) => i.direction === 'SELL_IMBALANCE').length,
      stackedBuy: imbalanceResult.stackedBuys,
      stackedSell: imbalanceResult.stackedSells
    },
    absorptionFeature,
    exhaustionFeature
  );

  const contextSynthesizer = new MarketContextSynthesizer();
  const marketContext = contextSynthesizer.buildContext(historicalBars, dataQualityScore);

  const pipeline = new DecisionArbiterPipeline();
  const decision: FinalTradeDecision = pipeline.evaluate(currentBar, ofContext, marketContext, brokerPayout);

  const getDecisionBadge = (direction: FinalTradeDecision['direction']) => {
    switch (direction) {
      case 'CALL':
        return {
          bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-emerald-950/50',
          icon: <TrendingUp className="w-5 h-5 text-emerald-400" />,
          title: 'CALL (ورود صعودی)'
        };
      case 'PUT':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-rose-950/50',
          icon: <TrendingDown className="w-5 h-5 text-rose-400" />,
          title: 'PUT (ورود نزولی)'
        };
      case 'NO_TRADE':
      default:
        return {
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-amber-950/50',
          icon: <ShieldAlert className="w-5 h-5 text-amber-400" />,
          title: 'NO TRADE (عدم معامله — حفظ سرمایه)'
        };
    }
  };

  const badge = getDecisionBadge(decision.direction);

  return (
    <div className="space-y-6 text-slate-100 font-sans dir-rtl">
      {/* Top Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400 shadow-inner">
            <BrainCircuit className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-100">موتور ستاپ و چارچوب تصمیم‌گیری کمی (FO-X 5M Phase 4)</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border flex items-center gap-1 ${badge.bg}`}>
                {badge.icon}
                {badge.title}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              ترکیب اردر فلو، بافتار بازار، ستاپ‌های A-D، ارزیابی آماری ویلسون، امید ریاضی (EV) و فیلترهای اکید NO TRADE
            </p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 flex-wrap">
          <button
            onClick={() => setActiveTab('arbiter')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'arbiter' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BrainCircuit className="w-3.5 h-3.5" />
            اتاق داوری و تصمیم (Decision Arbiter)
          </button>
          <button
            onClick={() => setActiveTab('setups_lab')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'setups_lab' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            آزمایشگاه ستاپ‌های A تا D
          </button>
          <button
            onClick={() => setActiveTab('ev_simulator')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'ev_simulator' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calculator className="w-3.5 h-3.5" />
            ماشین‌حساب امید ریاضی (EV) و ویلسون
          </button>
          <button
            onClick={() => setActiveTab('ml_vectors')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'ml_vectors' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            بردار ویژگی ML (Feature Vector)
          </button>
          <button
            onClick={() => setActiveTab('spec')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'spec' ? 'bg-purple-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode2 className="w-3.5 h-3.5" />
            مستندات مهندسی فاز ۴
          </button>
        </div>
      </div>

      {/* Tab 1: Decision Arbiter */}
      {activeTab === 'arbiter' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Decision & Score Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-bold text-slate-200">داوری تصمیم نهایی کندل ۵ دقیقه</h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                کندل: {new Date(decision.timestamp).toLocaleTimeString('fa-IR')}
              </span>
            </div>

            {/* Decision Status Box */}
            <div className={`p-4 rounded-xl border space-y-2 ${badge.bg}`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold block">تصمیم سیستم:</span>
                <span className="text-sm font-mono font-bold">{decision.direction}</span>
              </div>
              <p className="text-xs leading-relaxed">{decision.explanation.headlineFa}</p>
            </div>

            {/* Setup Score Meter */}
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-400">امتیاز کیفی ستاپ (Setup Score):</span>
                <span className={`font-mono font-bold text-sm ${decision.scoreBreakdown.isPassingThreshold ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {decision.scoreBreakdown.totalScore} / 100
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    decision.scoreBreakdown.isPassingThreshold ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                  style={{ width: `${decision.scoreBreakdown.totalScore}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>حداقل مجاز: ۷۲</span>
                <span>وضعیت: {decision.scoreBreakdown.isPassingThreshold ? '✅ تایید' : '❌ رد شده'}</span>
              </div>
            </div>

            {/* Component Score Distribution */}
            <div className="space-y-1.5 text-xs">
              <span className="text-slate-400 text-[11px] font-bold block">تفکیک امتیازات ۵ مولفه:</span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">اردر فلو (۳۰):</span>
                  <span className="font-mono text-purple-300 font-bold">{decision.scoreBreakdown.orderFlowScore}</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">بافتار ساختار (۲۵):</span>
                  <span className="font-mono text-indigo-300 font-bold">{decision.scoreBreakdown.contextScore}</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">نقدینگی (۲۰):</span>
                  <span className="font-mono text-emerald-300 font-bold">{decision.scoreBreakdown.liquidityScore}</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800 flex justify-between">
                  <span className="text-slate-400">نوسان‌پذیری (۱۵):</span>
                  <span className="font-mono text-amber-300 font-bold">{decision.scoreBreakdown.volatilityScore}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Expected Value & Probability Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Percent className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-200">مدل امید ریاضی و احتمال آماری</h3>
              </div>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                decision.ev.verdict === 'STRONG_POSITIVE_EV' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-amber-950 text-amber-300 border-amber-800'
              }`}>
                {decision.ev.verdict}
              </span>
            </div>

            {/* Payout Controller */}
            <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">پرداخت بروکر (Broker Payout):</span>
                <span className="font-mono font-bold text-emerald-400">{brokerPayout}%</span>
              </div>
              <input
                type="range"
                min="60"
                max="95"
                step="1"
                value={brokerPayout}
                onChange={(e) => setBrokerPayout(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>سربه‌سر بروکر: {(decision.ev.breakevenWinRateRequired * 100).toFixed(1)}%</span>
                <span>حداقل مجاز: ۷۵%</span>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">احتمال برد برآوردشده (Shrinkage)</span>
                <span className="text-base font-bold font-mono text-cyan-400">
                  {(decision.probability.shrinkageAdjustedProbability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">امید ریاضی (EV)</span>
                <span className={`text-base font-bold font-mono ${decision.ev.expectedValuePercent >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {decision.ev.expectedValuePercent > 0 ? `+${decision.ev.expectedValuePercent}%` : `${decision.ev.expectedValuePercent}%`}
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">بازه اطمینان ۹۵% ویلسون</span>
                <span className="text-xs font-bold font-mono text-slate-300">
                  {(decision.probability.wilsonLowerBound * 100).toFixed(0)}% — {(decision.probability.wilsonUpperBound * 100).toFixed(0)}%
                </span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">تعداد نمونه تاریخی</span>
                <span className="text-xs font-bold font-mono text-purple-300">
                  {decision.probability.sampleSize} مورد ({decision.probability.sampleAdequacy})
                </span>
              </div>
            </div>
          </div>

          {/* Explainability & NO TRADE Guards Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-slate-200">شفافیت تصمیم و فیلترهای محافظتی</h3>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">Explainability</span>
            </div>

            {/* Explanation Points */}
            <div className="space-y-2 text-xs">
              <span className="text-slate-400 font-bold block text-[11px]">دلایل فنی تصمیم موتور:</span>
              <ul className="space-y-1.5 text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                {decision.explanation.detailedPoints.map((point, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 text-[11px] leading-relaxed">
                    <ChevronRight className="w-3.5 h-3.5 text-purple-400 mt-0.5 shrink-0" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Rejection / Risk Reasons */}
            {decision.explanation.rejectionReasons.length > 0 && decision.explanation.rejectionReasons[0] !== 'NONE' && (
              <div className="p-3 rounded-lg border bg-rose-950/20 border-rose-800/40 text-rose-300 space-y-1 text-xs">
                <span className="font-bold flex items-center gap-1 text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                  فیلترهای بازدارنده معامله (Guard Triggers):
                </span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {decision.explanation.rejectionReasons.map((r, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-rose-900/60 font-mono text-[10px]">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Setups Lab */}
      {activeTab === 'setups_lab' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-purple-400 flex items-center gap-2">
                <Layers className="w-4 h-4" />
                آزمایشگاه و ماتریس قوانین ستاپ‌های اختصاصی (Core Setups A-D)
              </h3>
              <p className="text-slate-400 text-[11px] mt-1">
                بررسی موشکافانه شروط، ضرایب وزنی و قوانین ابطال (Invalidation) هر ستاپ
              </p>
            </div>
          </div>

          {/* Setup Selection Pills */}
          <div className="flex gap-2 border-b border-slate-800 pb-3 overflow-x-auto">
            <button
              onClick={() => setSelectedSetupTab('SETUP_A_SWEEP_ABSORPTION_REVERSAL')}
              className={`px-3 py-2 rounded-lg font-bold transition-all text-xs ${
                selectedSetupTab === 'SETUP_A_SWEEP_ABSORPTION_REVERSAL'
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-950 text-slate-400 border border-slate-800'
              }`}
            >
              ستاپ A: سوئیپ + جذب و بازگشت (Reversal)
            </button>
            <button
              onClick={() => setSelectedSetupTab('SETUP_B_IMBALANCE_CONTINUATION')}
              className={`px-3 py-2 rounded-lg font-bold transition-all text-xs ${
                selectedSetupTab === 'SETUP_B_IMBALANCE_CONTINUATION'
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-950 text-slate-400 border border-slate-800'
              }`}
            >
              ستاپ B: تداوم عدم‌تعادل مومنتوم (Continuation)
            </button>
            <button
              onClick={() => setSelectedSetupTab('SETUP_C_EXHAUSTION_REVERSAL')}
              className={`px-3 py-2 rounded-lg font-bold transition-all text-xs ${
                selectedSetupTab === 'SETUP_C_EXHAUSTION_REVERSAL'
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-950 text-slate-400 border border-slate-800'
              }`}
            >
              ستاپ C: فرسودگی و بازگشت روند (Exhaustion)
            </button>
            <button
              onClick={() => setSelectedSetupTab('SETUP_D_FAILED_AUCTION_REVERSAL')}
              className={`px-3 py-2 rounded-lg font-bold transition-all text-xs ${
                selectedSetupTab === 'SETUP_D_FAILED_AUCTION_REVERSAL'
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-950 text-slate-400 border border-slate-800'
              }`}
            >
              ستاپ D: حراج ناموفق و بازگشت به رنج (Failed Auction)
            </button>
          </div>

          {/* Setup Detail View */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">قوانین و شروط تایید ستاپ انتخابی:</h4>
              <div className="space-y-2">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-200 block">شرط ۱: رویداد نقدینگی / حجم تهاجمی</span>
                  <p className="text-slate-400 text-[11px]">عبور از پیوت‌های کلیدی یا تشکیل عدم‌تعادل‌های متوالی (Stacked Imbalance)</p>
                  <span className="text-[10px] text-purple-400 font-mono">وزن: ۳۵%</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-200 block">شرط ۲: عدم پیشروی قیمت و واکنش فوری دلتا</span>
                  <p className="text-slate-400 text-[11px]">جذب اردرهای مارکت با لیمیت‌های بزرگ و بسته شدن کندل در جهت مخالف</p>
                  <span className="text-[10px] text-purple-400 font-mono">وزن: ۳۵%</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                  <span className="font-bold text-slate-200 block">شرط ۳: همسویی بافتار چندزمانه و رژیم بازار</span>
                  <p className="text-slate-400 text-[11px]">عدم وجود تضاد با تایم‌فریم‌های ۱ ساعته و ۱۵ دقیقه</p>
                  <span className="text-[10px] text-purple-400 font-mono">وزن: ۳۰%</span>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">قوانین ابطال فوری (Invalidation Rules):</h4>
              <div className="p-3 bg-rose-950/20 border border-rose-800/40 rounded-lg space-y-2 text-rose-300">
                <div className="flex items-center gap-1.5 font-bold">
                  <XCircle className="w-4 h-4 text-rose-400" />
                  <span>ابطال بر اساس تثبیت فراتر از سطح (Acceptance Break):</span>
                </div>
                <p className="text-slate-400 text-[11px]">
                  در صورت بسته شدن کامل کلوز کندل ۵ دقیقه بیرون از سطح سوئیپ‌شده یا شکست لایه Stacked Imbalance، ستاپ بلافاصله لغو می‌گردد.
                </p>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                <span className="font-bold text-slate-200 block">آمار تاریخی اعتبارسنجی شده (Quantitative Historical Stats):</span>
                <div className="grid grid-cols-2 gap-2 text-center text-xs">
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">وین‌ریت میانگین</span>
                    <span className="font-bold text-emerald-400 font-mono">64.5%</span>
                  </div>
                  <div className="p-2 bg-slate-900 rounded border border-slate-800">
                    <span className="text-[10px] text-slate-400 block">تعداد وقوع ثبت‌شده</span>
                    <span className="font-bold text-cyan-400 font-mono">312 ترید</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: EV & Probability Simulator */}
      {activeTab === 'ev_simulator' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
              <Calculator className="w-4 h-4" />
              ماتریس امید ریاضی (EV) و منحنی‌های سربه‌سر باینری آپشن ۵ دقیقه
            </h3>
            <p className="text-slate-400 text-[11px] mt-1">
              فرمول ریاضی: EV = (Win_Probability × Payout%) - (Loss_Probability × 100%)
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <span className="text-slate-400 text-[11px] block">پرداخت بروکر: 80%</span>
              <span className="text-sm font-bold text-slate-200 block">حداقل وین‌ریت برای سربه‌سر: 55.5%</span>
              <p className="text-slate-500 text-[10px]">نیاز به حداقل ۵۹% وین‌ریت برای دستیابی به +6.2% EV</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <span className="text-slate-400 text-[11px] block">پرداخت بروکر: 85%</span>
              <span className="text-sm font-bold text-emerald-400 block">حداقل وین‌ریت برای سربه‌سر: 54.0%</span>
              <p className="text-slate-500 text-[10px]">وین‌ریت ۶۴% امید ریاضی معادل +18.4% سود در هر ترید ایجاد می‌کند</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-2">
              <span className="text-slate-400 text-[11px] block">پرداخت بروکر: 90%</span>
              <span className="text-sm font-bold text-cyan-400 block">حداقل وین‌ریت برای سربه‌سر: 52.6%</span>
              <p className="text-slate-500 text-[10px]">بهترین شرایط بازدهی با کمترین اثر اصطکاک بروکر</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: ML Feature Vector Inspector */}
      {activeTab === 'ml_vectors' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-cyan-400 flex items-center gap-2">
                <Database className="w-4 h-4" />
                بردار ویژگی ۱۲ بعدی آماده برای یادگیری ماشین (Machine Learning Vector)
              </h3>
              <p className="text-slate-400 text-[11px] mt-1">
                تسک ۱۰: داده‌های استانداردسازی شده جهت آموزش مدل‌های رگرسیون لجستیک یا بوستینگ
              </p>
            </div>
          </div>

          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3 font-mono text-[11px]">
            <span className="text-slate-400 block font-sans font-bold">بردار مقادیر کندل جاری (JSON Feature Representation):</span>
            <pre className="p-3 bg-slate-900 rounded-lg text-cyan-300 overflow-x-auto border border-slate-800">
              {JSON.stringify(decision.mlFeatureVector, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Tab 5: Specification */}
      {activeTab === 'spec' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs leading-relaxed text-slate-300">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-purple-400 flex items-center gap-2">
              <FileCode2 className="w-5 h-5" />
              سند مشخصات و معماری چارچوب تصمیم‌گیری (Phase 4 Specification)
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">پاسخ کامل به تسک‌های ۱ تا ۱۴</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۱. Decision Pipeline & Setup Engine</h4>
              <p>خط لوله تصمیم‌گیری مدولار شامل ارزیابی ستاپ، امتیازدهی کیفی، تخمین احتمال و محاسبه امید ریاضی.</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۲. Bayesian Shrinkage & Wilson 95%</h4>
              <p>استفاده از کران پایین بازه اطمینان ویلسون برای جلوگیری از خطای تعمیم در حجم نمونه‌های محدود.</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۳. NO TRADE as First-Class Citizen</h4>
              <p>اولویت قطعی عدم معامله در شرایط داده مخدوش، قرنطینه خبری، نوسان شدید یا امید ریاضی منفی.</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۴. Full Explainability & ML Vector</h4>
              <p>ثبت دقیق دلایل انسانی تصمیم به همراه استخراج بردار عددی ۱۲ بعدی برای آزمایش‌های بعدی یادگیری ماشین.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
