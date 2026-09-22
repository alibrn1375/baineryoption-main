import React, { useState } from 'react';
import { Database, ShieldCheck, Activity, Cpu, Layers, HardDrive, RefreshCw, AlertOctagon, CheckCircle2, Play, Pause } from 'lucide-react';
import { DataQualityReport, QualityState, TickEntity, DeltaEngineState } from '../types/dataPipeline';

interface PipelineInspectorViewProps {
  currentQualityReport: DataQualityReport;
  deltaState: DeltaEngineState;
  processedTickCount: number;
  onSimulateTickAnomaly: (type: 'DUPLICATE' | 'OUT_OF_ORDER' | 'INVALID_SPREAD' | 'SYNC_ANOMALY') => void;
  onResetQuality: () => void;
}

export const PipelineInspectorView: React.FC<PipelineInspectorViewProps> = ({
  currentQualityReport,
  deltaState,
  processedTickCount,
  onSimulateTickAnomaly,
  onResetQuality
}) => {
  const [activePipelineTab, setActivePipelineTab] = useState<'overview' | 'providers' | 'storage' | 'replay' | 'spec'>('overview');

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
    if (score >= 50) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
  };

  const getStateBadge = (state: QualityState) => {
    if (state === 'GOOD') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5" />
          GOOD DATA (100% قابل اتکا)
        </span>
      );
    }
    if (state === 'DEGRADED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
          <Activity className="w-3.5 h-3.5" />
          DEGRADED DATA (هشدار افت کیفیت)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <AlertOctagon className="w-3.5 h-3.5" />
        INVALID DATA (توقف اضطراری پردازش)
      </span>
    );
  };

  return (
    <div className="space-y-6" id="pipeline-inspector">
      
      {/* Sub Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto">
        <button
          onClick={() => setActivePipelineTab('overview')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activePipelineTab === 'overview'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          موتور پایش کیفیت داده و دلتا (Data Quality & Delta Engine)
        </button>
        <button
          onClick={() => setActivePipelineTab('providers')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activePipelineTab === 'providers'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          پرووایدرهای انتزاعی (GC Futures & Spot & News)
        </button>
        <button
          onClick={() => setActivePipelineTab('storage')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activePipelineTab === 'storage'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          معماری ذخیره‌سازی داده (Parquet / DuckDB Schema)
        </button>
        <button
          onClick={() => setActivePipelineTab('replay')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activePipelineTab === 'replay'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          موتور بازپخش تیک و پیشگیری از Lookahead Bias
        </button>
        <button
          onClick={() => setActivePipelineTab('spec')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            activePipelineTab === 'spec'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          سند مهندسی ۱۰گانه فاز ۱ (Engineering Spec)
        </button>
      </div>

      {activePipelineTab === 'overview' && (
        <>
          {/* Top Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>امتیاز کیفیت داده (Score)</span>
                <ShieldCheck className="w-4 h-4 text-slate-500" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className={`text-2xl font-mono font-bold ${getScoreColor(currentQualityReport.score).split(' ')[0]}`}>
                  {currentQualityReport.score}
                </span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
              <div className="mt-2">{getStateBadge(currentQualityReport.state)}</div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>تعداد تیک‌های پردازش‌شده</span>
                <Activity className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-mono font-bold text-slate-100">
                {processedTickCount.toLocaleString()}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">تیک‌های میکروثانیه بورس CME</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>دلتای شمع جاری (Candle Delta)</span>
                <Cpu className="w-4 h-4 text-purple-400" />
              </div>
              <div className={`text-2xl font-mono font-bold ${deltaState.candleDelta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {deltaState.candleDelta > 0 ? `+${deltaState.candleDelta}` : deltaState.candleDelta}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">فرمول: Ask Volume - Bid Volume</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>دلتای تجمعی نشست (Session CVD)</span>
                <Layers className="w-4 h-4 text-amber-400" />
              </div>
              <div className={`text-2xl font-mono font-bold ${deltaState.sessionCvd >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {deltaState.sessionCvd > 0 ? `+${deltaState.sessionCvd}` : deltaState.sessionCvd}
              </div>
              <p className="text-[11px] text-slate-500 mt-1">ریست خودکار در شروع سشن نیویورک</p>
            </div>
          </div>

          {/* Anomaly Testing & Quality Reasons Box */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Realtime Anomaly & Quality Logs */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  وضعیت سنسورهای مانیتورینگ خط لوله داده
                </h3>
                <button
                  onClick={onResetQuality}
                  className="px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 border border-slate-700"
                >
                  <RefreshCw className="w-3 h-3" />
                  ریست سنسورها
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <span className="text-slate-400">تاخیر فید سرور (Feed Latency):</span>
                  <span className="font-mono text-emerald-400 font-bold">{currentQualityReport.feedDelayMs} ms</span>
                </div>

                <div className="flex justify-between items-center p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <span className="text-slate-400">ناهماهنگی زمانی تیک‌ها (Out of Order):</span>
                  <span className={`font-mono font-bold ${currentQualityReport.outOfOrderFixed > 0 ? 'text-amber-400' : 'text-slate-300'}`}>
                    {currentQualityReport.outOfOrderFixed} مورد اصلاح شد
                  </span>
                </div>

                <div className="flex justify-between items-center p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <span className="text-slate-400">تیک‌های تکراری حذف‌شده (Duplicates Dropped):</span>
                  <span className={`font-mono font-bold ${currentQualityReport.duplicateTicksDropped > 0 ? 'text-amber-400' : 'text-slate-300'}`}>
                    {currentQualityReport.duplicateTicksDropped} تیک
                  </span>
                </div>

                <div className="flex justify-between items-center p-2.5 rounded-lg bg-slate-950 border border-slate-800/80">
                  <span className="text-slate-400">اختلاف زمانی همگام‌سازی GC و XAU (Basis Sync):</span>
                  <span className="font-mono text-slate-300 font-bold">{currentQualityReport.syncOffsetMs.toFixed(2)}$</span>
                </div>

                {/* Failure Log */}
                {currentQualityReport.reasons.length > 0 && (
                  <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 space-y-1">
                    <span className="font-bold block">خطاهای کشف‌شده در آخرین فریم:</span>
                    {currentQualityReport.reasons.map((r, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-[11px]">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                        <span>{r}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Simulated Edge-Case Testing Controls */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
              <h3 className="text-sm font-bold text-slate-200 mb-2 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                تست تاب‌آوری و اعتبارسنجی Edge-Cases (تسک ۱۰)
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                تزریق خطاهای عمدی برای راستی‌آزمایی مکانیزم توقف اضطراری (Halt Processing) و فیلتر داده‌های مخدوش:
              </p>

              <div className="grid grid-cols-2 gap-2.5">
                <button
                  onClick={() => onSimulateTickAnomaly('DUPLICATE')}
                  className="p-2.5 text-xs rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-amber-500/40 text-right transition-all"
                >
                  <span className="font-bold block text-amber-400">تزریق تیک تکراری</span>
                  <span className="text-[10px] text-slate-500">آزمون Deduplication</span>
                </button>

                <button
                  onClick={() => onSimulateTickAnomaly('OUT_OF_ORDER')}
                  className="p-2.5 text-xs rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-amber-500/40 text-right transition-all"
                >
                  <span className="font-bold block text-amber-400">تیک با تاخیر زمانی</span>
                  <span className="text-[10px] text-slate-500">آزمون Out-of-Order Timestamp</span>
                </button>

                <button
                  onClick={() => onSimulateTickAnomaly('INVALID_SPREAD')}
                  className="p-2.5 text-xs rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-rose-500/40 text-right transition-all"
                >
                  <span className="font-bold block text-rose-400">اسپرد منفی (Bid &gt; Ask)</span>
                  <span className="text-[10px] text-slate-500">افت مستقیم به INVALID DATA</span>
                </button>

                <button
                  onClick={() => onSimulateTickAnomaly('SYNC_ANOMALY')}
                  className="p-2.5 text-xs rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-rose-500/40 text-right transition-all"
                >
                  <span className="font-bold block text-rose-400">ناهماهنگی قیمت فیوچرز/اسپات</span>
                  <span className="text-[10px] text-slate-500">تست Basis Desynchronization</span>
                </button>
              </div>

              <div className="mt-4 p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 text-xs">
                <span className="text-amber-400 font-bold block mb-1">رفتار سیستم در صورت INVALID DATA:</span>
                قطع بلافاصله خروجی موتور پردازش، لغو هرگونه ثبت سفارش و ثبت لاگ توقف اضطراری در دیتابیس DuckDB.
              </div>
            </div>

          </div>
        </>
      )}

      {activePipelineTab === 'providers' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h4 className="text-sm font-bold text-amber-400 mb-2 flex items-center gap-2">
              <Database className="w-4 h-4" />
              GC Futures Provider (CME L2/L3)
            </h4>
            <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside leading-relaxed">
              <li><strong className="text-slate-100">ورودی‌ها:</strong> Timestamp (میکروثانیه), Price, Size, Bid, Ask, Flag</li>
              <li><strong className="text-slate-100">تضمین:</strong> عدم استفاده از حجم میانگین و پایبندی ۱۰۰٪ به اردربوک واقعی</li>
              <li><strong className="text-slate-100">رفتار در خطا:</strong> در صورت قطع اتصال فید CME بیش از ۲ ثانیه، وضعیت کل سیستم بلافاصله DEGRADED می‌شود.</li>
            </ul>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h4 className="text-sm font-bold text-cyan-400 mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              XAU/USD Spot Provider
            </h4>
            <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside leading-relaxed">
              <li><strong className="text-slate-100">ورودی‌ها:</strong> Timestamp, Bid, Ask, Mid Price, Broker Spread</li>
              <li><strong className="text-slate-100">کاربرد:</strong> تطبیق قیمت اجرایی بروکر و محاسبه دقیق Basis Spread نسبت به فیوچرز</li>
              <li><strong className="text-slate-100">قانون:</strong> هرگز حجم اسپات برای ساخت فوت‌پرینت استفاده نمی‌شود.</li>
            </ul>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <h4 className="text-sm font-bold text-rose-400 mb-2 flex items-center gap-2">
              <AlertOctagon className="w-4 h-4" />
              Macro News Provider (Interface)
            </h4>
            <ul className="text-xs text-slate-300 space-y-2 list-disc list-inside leading-relaxed">
              <li><strong className="text-slate-100">ورودی‌ها:</strong> Event Title, Currency, Impact (High/Medium), Scheduled UTC Time</li>
              <li><strong className="text-slate-100">خروجی:</strong> پرچم قرنطینه خودکار (Quarantine Flag)</li>
              <li><strong className="text-slate-100">رفتار Fail-Safe:</strong> در صورت قطعی اتصال پرووایدر اخبار، سیستم به صورت خودکار محافظه‌کارانه عمل کرده و وضعیت را قرنطینه احتیاطی نگه می‌دارد.</li>
            </ul>
          </div>
        </div>
      )}

      {activePipelineTab === 'storage' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-2">
            <HardDrive className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-bold text-slate-100">طراحی پایگاه داده کمّی (DuckDB + Apache Parquet)</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            جهت ذخیره‌سازی میلیاردها تیک و بازیابی میلی‌ثانیه‌ای ماتریس فوت‌پرینت، از قالب ذخیره‌سازی ستونی (Columnar Storage) با فرمت Apache Parquet به همراه موتور تحلیلی DuckDB بدون سرور استفاده می‌شود.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-amber-400 font-bold block mb-2">جدول raw_ticks (تیک‌های خام):</span>
              <pre className="text-slate-400 text-[11px] leading-relaxed">
{`CREATE TABLE raw_ticks (
  tick_id VARCHAR PRIMARY KEY,
  timestamp_utc TIMESTAMP_NS,
  symbol VARCHAR(10),
  price DECIMAL(8, 2),
  size INT,
  bid DECIMAL(8, 2),
  ask DECIMAL(8, 2),
  aggressor_side VARCHAR(8) -- BUY / SELL / UNKNOWN
);`}
              </pre>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-cyan-400 font-bold block mb-2">جدول footprint_bars_5m (شمع‌های فوت‌پرینت):</span>
              <pre className="text-slate-400 text-[11px] leading-relaxed">
{`CREATE TABLE footprint_bars_5m (
  bar_id VARCHAR PRIMARY KEY,
  bar_start_utc TIMESTAMP,
  open DECIMAL(8,2), high DECIMAL(8,2),
  low DECIMAL(8,2), close DECIMAL(8,2),
  total_volume BIGINT,
  total_delta BIGINT,
  session_cvd BIGINT,
  poc_price DECIMAL(8,2),
  levels_json JSON
);`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {activePipelineTab === 'replay' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-purple-400" />
            <h3 className="text-base font-bold text-slate-100">موتور بازپخش تیک (Historical Replay) و حذف کامل Look-Ahead Bias</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            در این معماری، دقیقاً همان کلاسی که وظیفه پردازش تیک‌های لایو را دارد (<code className="text-amber-300">FootprintEngine</code>)، به عنوان مصرف‌کننده فید بازپخش تیک‌های تاریخی (Tick Replayer) استفاده می‌شود. موتور هیچ اطلاعی از تیک‌های بعدی نداشته و شمع ۵ دقیقه‌ای تیک‌به‌تیک در زمان واقعی ساخته می‌شود تا از سوگیری نگاه به آینده (Look-Ahead Bias) جلوگیری کامل به عمل آید.
          </p>

          <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs text-slate-400 space-y-2">
            <span className="font-bold text-emerald-400 block">اصول مهندسی Replay Engine:</span>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>اجرای تیک‌ها دقیقاً با ترتیب زمانی Timestamp میکروثانیه</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>محاسبه دلتا و CVD دقیقاً در لحظه دریافت هر تیک و بدون دسترسی به کل شمع</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>بررسی شرایط خروج و استاپ‌لاس در انقضای ۵ دقیقه دقیقاً مطابق با جریان قیمت آنی</span>
            </div>
          </div>
        </div>
      )}

      {activePipelineTab === 'spec' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6 text-xs text-slate-300 leading-relaxed">
          <div className="border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-amber-400 flex items-center gap-2">
              <Layers className="w-5 h-5" />
              سند مشخصات مهندسی زیرساخت داده و موتور فوت‌پرینت (FO-X 5M — Phase 1 Specification)
            </h3>
            <p className="text-[11px] text-slate-400 mt-1">پاسخ کامل به تمام ۱۰ تسک الزامی معماری پایپ‌لاین داده و اردر فلو</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۱. Data Architecture & Pipeline Flow</h4>
              <p>مسیر حرکتی داده: Raw Market Ticks &rarr; Normalization &rarr; Validation Engine &rarr; DuckDB/Parquet Storage &rarr; Footprint Synthesis Engine. جریان لایو و Replay از موتور پردازشی کاملاً یکسانی استفاده می‌کنند.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۲. Provider Interfaces (GC Futures, Spot, News)</h4>
              <p>جداسازی کامل فید فیوچرز CME (مرجع اردر فلو) از قیمت اسپات XAUUSD (مرجع اجرای بروکر). اینترفیس اخبار بدون ساخت منطق سیگنال، پرچم قرنطینه خودکار را مدیریت می‌کند.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۳. Tick Data Model & Trade Classification</h4>
              <p>هر تیک حاوی قیمت، حجم، Bid، Ask، Timestamp میکروثانیه و سمت معامله (BUY / SELL / UNKNOWN). تیک‌های UNKNOWN از الگوریتم Lee-Ready پیروی کرده و در صورت ابهام، جهت عدم تخریب دلتا نوین می‌مانند.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۴. Data Quality System & Halt Protocol</h4>
              <p>سیستم پایش ۰ تا ۱۰۰ با سه حالت GOOD (80-100)، DEGRADED (50-79) و INVALID (&lt;50). در حالت INVALID، پردازش بلافاصله متوقف گردیده (Emergency Halt) و خروجی صادر نمی‌شود.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۵. Footprint Engine Design</h4>
              <p>تبدیل تیک‌ها به شمع‌های ۵ دقیقه‌ای، ساخت لدر قیمت با گام ۰.۵۰$، محاسبه عدم‌تعادل‌های قطری ۳۰۰٪ (Diagonal Imbalances) و شناسایی جذب نقدینگی (Passive Absorption).</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۶ & ۷. Delta Engine & Session CVD</h4>
              <p>فرمول: Delta = Ask Vol - Bid Vol. پشتیبانی از دلتای شمع، دلتای ۵ دقیقه، دلتای سشن و دلتای نوسان (Swing Delta) با ریست خودکار در شروع سشن نیویورک.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۸. Storage Architecture (DuckDB / Parquet)</h4>
              <p>ذخیره‌سازی ستونی تیک‌های خام و شمع‌های فوت‌پرینت با DuckDB و Parquet جهت حداکثر بازدهی در کوئری‌های کمّی و بک‌تستینگ.</p>
            </div>

            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
              <h4 className="font-bold text-slate-100 text-sm">۹ & ۱۰. Replay Engine & Testing Strategy</h4>
              <p>بازپخش تیک‌به‌تیک دقیقاً مطابق فید زنده جهت حذف کامل Look-ahead Bias و تست‌های واحد برای صحت محاسبات اردر فلو.</p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
