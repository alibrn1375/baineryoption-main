import React, { useState } from 'react';
import {
  Globe,
  Compass,
  Layers,
  Zap,
  Activity,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Radio,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Target,
  FileText,
  Sliders
} from 'lucide-react';
import { FootprintBar } from '../types';
import { MarketContext, NewsRiskState, VolatilityLevel } from '../types/marketContext';
import { MarketContextSynthesizer } from '../services/marketContextService';

interface MarketContextInspectorViewProps {
  bars: FootprintBar[];
  dataQualityScore: number;
}

export const MarketContextInspectorView: React.FC<MarketContextInspectorViewProps> = ({
  bars,
  dataQualityScore
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'structure' | 'liquidity' | 'risk_news' | 'spec'>('overview');
  const [simulatedNewsRisk, setSimulatedNewsRisk] = useState<NewsRiskState | null>(null);

  const contextSynthesizer = new MarketContextSynthesizer();
  const baseContext = contextSynthesizer.buildContext(bars, dataQualityScore);

  // Apply simulation if selected
  const context: MarketContext = simulatedNewsRisk
    ? {
        ...baseContext,
        newsRisk: {
          ...baseContext.newsRisk,
          state: simulatedNewsRisk,
          tradingAllowed: simulatedNewsRisk === 'NORMAL' || simulatedNewsRisk === 'ELEVATED',
          reason: `تست دستی حالت خبری: ${simulatedNewsRisk}`
        },
        overallEnvironmentSuitability:
          simulatedNewsRisk === 'BLOCKED' || simulatedNewsRisk === 'POST_EVENT_REASSESSMENT'
            ? 'PROHIBITED'
            : simulatedNewsRisk === 'ELEVATED'
            ? 'HIGH_RISK_FILTERED'
            : baseContext.overallEnvironmentSuitability
      }
    : baseContext;

  const getSuitabilityBadge = (suitability: MarketContext['overallEnvironmentSuitability']) => {
    switch (suitability) {
      case 'FAVORABLE':
        return {
          bg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
          text: '✅ شرایط محیطی مساعد (Favorable)'
        };
      case 'MODERATE_CAUTION':
        return {
          bg: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
          text: '⚠️ احتیاط متوسط (Moderate Caution)'
        };
      case 'HIGH_RISK_FILTERED':
        return {
          bg: 'bg-orange-500/20 text-orange-300 border-orange-500/40',
          text: '⚡ پرریسک / فیلترشده (High Risk)'
        };
      case 'PROHIBITED':
        return {
          bg: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
          text: '⛔ معامله مطلقا ممنوع (Prohibited)'
        };
    }
  };

  const badge = getSuitabilityBadge(context.overallEnvironmentSuitability);

  return (
    <div className="space-y-6 text-slate-100 font-sans dir-rtl">
      {/* Header Banner */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 shadow-inner">
            <Compass className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-100">بافتار بازار و مدیریت ریسک محیطی (FO-X 5M Phase 3)</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badge.bg}`}>
                {badge.text}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              تحلیل چندزمانه (MTF)، تشخیص ساختار، نقدینگی استاتیک و ساختاری، سوئیپ‌ها و فیلترهای خبری
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 flex-wrap">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'overview'
                ? 'bg-indigo-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            نمای کلی بافتار (Overview)
          </button>
          <button
            onClick={() => setActiveTab('structure')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'structure'
                ? 'bg-indigo-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            سوینگ‌ها و شکست ساختار (BOS/CHoCH)
          </button>
          <button
            onClick={() => setActiveTab('liquidity')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'liquidity'
                ? 'bg-indigo-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            نقشه نقدینگی و سوئیپ‌ها (Liquidity)
          </button>
          <button
            onClick={() => setActiveTab('risk_news')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'risk_news'
                ? 'bg-indigo-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            سشن و فیلترهای خبری (Risk & News)
          </button>
          <button
            onClick={() => setActiveTab('spec')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === 'spec'
                ? 'bg-indigo-500 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            سند مشخصات فاز ۳
          </button>
        </div>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card 1: Regime & MTF Alignment */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-200">رژیم بازار و همسویی چندزمانه</h3>
              </div>
              <span className="text-[11px] font-mono text-indigo-400 bg-indigo-950/60 border border-indigo-800/50 px-2 py-0.5 rounded-md">
                اطمینان: {context.regimeState.confidence}%
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
              <span className="text-slate-400 text-[11px] block">رژیم جاری ۵ دقیقه:</span>
              <span className="text-base font-bold text-indigo-300 font-mono">
                {context.regimeState.state}
              </span>
              <span className="text-[11px] text-slate-500 block">
                تداوم روند: {context.regimeState.trendPersistenceBars} کندل متوالی
              </span>
            </div>

            {/* MTF Matrix */}
            <div className="space-y-2 text-xs">
              <span className="text-slate-400 font-bold block text-[11px]">ماتریس همسویی تایم‌فریم‌ها:</span>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 bg-slate-950 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">1H Macro</span>
                  <span className="font-bold text-emerald-400 text-[11px]">BULLISH</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">15M Context</span>
                  <span className="font-bold text-cyan-400 text-[11px]">PULLBACK</span>
                </div>
                <div className="p-2 bg-slate-950 rounded border border-slate-800">
                  <span className="text-[10px] text-slate-500 block">5M Trigger</span>
                  <span className="font-bold text-amber-400 text-[11px]">{context.mtfContext.primaryTimeframe5M.structure}</span>
                </div>
              </div>
              <div className="p-2 bg-slate-950/90 rounded border border-slate-800 flex justify-between items-center text-[11px]">
                <span className="text-slate-400">وضعیت همسویی:</span>
                <span className="font-bold text-emerald-400">{context.mtfContext.alignment} ({context.mtfContext.alignmentScore}%)</span>
              </div>
            </div>
          </div>

          {/* Card 2: Volatility Engine */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-200">موتور نوسان‌پذیری (Volatility Engine)</h3>
              </div>
              <span className={`text-[11px] font-mono px-2 py-0.5 rounded-md border ${
                context.volatilityState.level === 'NORMAL' ? 'bg-emerald-950 text-emerald-300 border-emerald-800' : 'bg-amber-950 text-amber-300 border-amber-800'
              }`}>
                {context.volatilityState.level}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">ATR (14)</span>
                <span className="text-base font-bold font-mono text-slate-200">${context.volatilityState.atr14}</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">نوسان سالانه تحقق‌یافته</span>
                <span className="text-base font-bold font-mono text-cyan-400">{context.volatilityState.realizedVolPercent}%</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">صدک دامنه کندل</span>
                <span className="text-sm font-bold font-mono text-amber-400">{context.volatilityState.candleRangePercentile}th %</span>
              </div>
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-slate-400 text-[11px] block">سرعت تیک (Ticks/sec)</span>
                <span className="text-sm font-bold font-mono text-indigo-300">{context.volatilityState.tickVelocityPerSecond} t/s</span>
              </div>
            </div>
          </div>

          {/* Card 3: Session & News Risk Environment */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4 shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-200">سشن معاملاتی و محیط ریسک</h3>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-2 py-0.5 rounded-md">
                {context.sessionState.currentSession}
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">اورلپ لندن / نیویورک:</span>
                <span className={`font-bold ${context.sessionState.isOverlapActive ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {context.sessionState.isOverlapActive ? '🟢 فعال (حجم سنگین)' : 'غیرفعال'}
                </span>
              </div>
              <div className="flex justify-between pt-1">
                <span className="text-slate-400">پروفایل نوسان سشن:</span>
                <span className="text-slate-200 font-mono">{context.sessionState.historicalVolatilityProfile}</span>
              </div>
            </div>

            {/* News Risk State */}
            <div className={`p-3 rounded-lg border text-xs space-y-1 ${
              context.newsRisk.tradingAllowed
                ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
                : 'bg-rose-950/30 border-rose-800/60 text-rose-300'
            }`}>
              <div className="flex justify-between font-bold">
                <span>فیلتر رویدادهای خبری:</span>
                <span>{context.newsRisk.state}</span>
              </div>
              <p className="text-[11px] text-slate-400">{context.newsRisk.reason}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Structure & Swings */}
      {activeTab === 'structure' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-indigo-400 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                سوینگ‌های تاییدشده و رویدادهای شکست ساختار (BOS / CHoCH)
              </h3>
              <p className="text-slate-400 text-[11px] mt-1">
                محاسبه بدون هرگونه نشت داده‌های آینده (Zero Lookahead Bias) با تایید ۲ کندل چپ و راست
              </p>
            </div>
            <span className="text-slate-400 font-mono">تعداد سوینگ‌های فعال: {context.swings.length}</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Swings List */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">آخرین نقاط سوینگ تاییدشده (Confirmed Swings):</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {context.swings.slice(-6).map((sw) => (
                  <div
                    key={sw.id}
                    className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      {sw.type === 'SWING_HIGH' ? (
                        <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-bold text-[10px]">
                          سوینگ سقف (High)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold text-[10px]">
                          سوینگ کف (Low)
                        </span>
                      )}
                      <span className="font-mono text-slate-200 text-xs">${sw.price.toFixed(2)}</span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">{new Date(sw.timestamp).toLocaleTimeString('fa-IR')}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Structure Events List */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">رویدادهای شکست ساختار (Structure Events):</h4>
              <div className="space-y-2">
                {context.structureEvents.length > 0 ? (
                  context.structureEvents.map((evt) => (
                    <div
                      key={evt.id}
                      className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-amber-300">{evt.type}</span>
                        <span className="text-[10px] text-slate-400 font-mono">{new Date(evt.breakoutCandleTimestamp).toLocaleTimeString('fa-IR')}</span>
                      </div>
                      <p className="text-slate-400 text-[11px]">
                        شکست سطح ${evt.brokenPriceLevel} با کلوز تاییدشده (قدرت: {evt.strength}%)
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-slate-500 text-center">
                    هیچ شکست ساختار تاییدشده جدیدی در ۵ دقیقه اخیر رخ نداده است.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Liquidity Map & Sweeps */}
      {activeTab === 'liquidity' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-sm font-bold text-emerald-400 flex items-center gap-2">
              <Target className="w-4 h-4" />
              نقشه استخر نقدینگی و سوئیپ‌های رخ‌داده (Liquidity Pools & Sweeps)
            </h3>
            <p className="text-slate-400 text-[11px] mt-1">
              سطوح استاتیک PDH/PDL، سقف و کف سشن، کف و سقف‌های مساوی (EQH/EQL)
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Liquidity Map */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">سطوح فعال نقدینگی (Active Liquidity Pools):</h4>
              <div className="space-y-2">
                {context.activeLiquidityLevels.map((lvl) => (
                  <div
                    key={lvl.id}
                    className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between"
                  >
                    <div>
                      <span className="font-bold text-slate-300 block">{lvl.type}</span>
                      <span className="text-[10px] text-slate-500 font-mono">تایم‌فریم: {lvl.timeframe}</span>
                    </div>
                    <span className="font-mono text-emerald-400 font-bold text-xs">${lvl.price.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Sweeps & Failed Auctions */}
            <div className="space-y-3">
              <h4 className="font-bold text-slate-200">سوئیپ‌های نقدینگی و حراج ناموفق (Failed Auctions):</h4>
              <div className="space-y-2">
                {context.recentSweeps.length > 0 ? (
                  context.recentSweeps.map((swp) => (
                    <div
                      key={swp.id}
                      className="p-3 bg-purple-950/30 border border-purple-800/50 rounded-lg space-y-1"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-purple-300">{swp.direction}</span>
                        <span className="text-[10px] font-mono text-slate-400">قدرت: {swp.strength}%</span>
                      </div>
                      <p className="text-slate-400 text-[11px]">
                        سوئیپ سطح {swp.sweptLevel.type} در قیمت ${swp.sweepPrice} و بازگشت به ${swp.rejectionClosePrice}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-slate-500 text-center">
                    هیچ سوئیپ نقدینگی در کندل اخیر رخ نداده است.
                  </div>
                )}

                {context.failedAuctions.map((fa) => (
                  <div
                    key={fa.id}
                    className="p-3 bg-amber-950/30 border border-amber-800/50 rounded-lg space-y-1"
                  >
                    <span className="font-bold text-amber-300 block">{fa.direction}</span>
                    <p className="text-slate-400 text-[11px]">
                      حراج ناموفق در سطح ${fa.breakoutLevel} و بازگشت سریع به درون محدوده ارزش (VA).
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: News & Risk Management Simulation */}
      {activeTab === 'risk_news' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs">
          <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-rose-400 flex items-center gap-2">
                <Radio className="w-4 h-4" />
                محیط ریسک خبری و شبیه‌سازی وضعیت‌های اضطراری
              </h3>
              <p className="text-slate-400 text-[11px] mt-1">
                تسک ۱۱ و ۱۲: قوانین قرنطینه پیش و پس از رویدادهای کلیدی (FOMC, CPI, NFP)
              </p>
            </div>
          </div>

          <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 space-y-3">
            <span className="font-bold text-slate-200 block">شبیه‌سازی واکنش موتور ریسک به حالات خبری:</span>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSimulatedNewsRisk(null)}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  simulatedNewsRisk === null ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                واقعی (Live Evaluation)
              </button>
              <button
                onClick={() => setSimulatedNewsRisk('NORMAL')}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  simulatedNewsRisk === 'NORMAL' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                حالت عادی (NORMAL)
              </button>
              <button
                onClick={() => setSimulatedNewsRisk('ELEVATED')}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  simulatedNewsRisk === 'ELEVATED' ? 'bg-amber-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                ریسک افزایشی (ELEVATED: T-30m)
              </button>
              <button
                onClick={() => setSimulatedNewsRisk('BLOCKED')}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  simulatedNewsRisk === 'BLOCKED' ? 'bg-rose-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                توقف کامل معاملات (BLOCKED: T-10m / Event)
              </button>
              <button
                onClick={() => setSimulatedNewsRisk('POST_EVENT_REASSESSMENT')}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs transition-all ${
                  simulatedNewsRisk === 'POST_EVENT_REASSESSMENT' ? 'bg-purple-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                دوره بازسنجی پس از خبر (POST_EVENT)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Phase 3 Engineering Spec */}
      {activeTab === 'spec' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6 shadow-xl text-xs leading-relaxed text-slate-300">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-indigo-400 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              سند مشخصات معماری بافتار بازار، نقدینگی و محیط ریسک (FO-X 5M Phase 3 Specification)
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">پاسخ کامل به تسک‌های ۱ تا ۱۷</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۱. Swings & Zero Lookahead Bias</h4>
              <p>تشخیص سوینگ‌های ماژور با ۲ کندل تایید سمت چپ و راست به صورت اکیداً بدون نشت داده‌های آینده (Zero Lookahead).</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۲. Market Structure (BOS / CHoCH)</h4>
              <p>شناسایی شکست ساختار پایدار با کلوز بدنه کندل (Confirmed Close) جهت محافظت در برابر Fakeoutهای نقدینگی.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۳. Liquidity Engine & Sweeps</h4>
              <p>رهگیری استاتیک PDH/PDL، سقف و کف سشن، سطوح EQH/EQL و تفکیک شکست واقعی از سوئیپ نقدینگی با بازگشت سریع.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۴. News Environment & Risk Model</h4>
              <p>مدل ۴ وضعیتی (NORMAL, ELEVATED, BLOCKED, POST_EVENT_REASSESSMENT) با توقف خودکار پردازش سیگنال در ۱۰ دقیقه قبل و حین اخبار.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
