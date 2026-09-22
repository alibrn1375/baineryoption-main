import React from 'react';
import { ShieldCheck, Cpu, Database, Network, GitBranch, AlertTriangle, Layers, Award, Terminal } from 'lucide-react';

export const ArchitectureView: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">سند معماری و مشخصات فنی موتور تحقیقاتی FO-X 5M</h2>
            <p className="text-xs text-slate-400">مبتنی بر استانداردهای مهندسی سیستم‌های کمّی نهادی (Institutional Quant Grade)</p>
          </div>
        </div>
      </div>

      {/* 10 Architectural Layers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-amber-400 mb-3 flex items-center gap-2">
            <Database className="w-4 h-4" />
            ۱. لایه دریافت و نرمال‌سازی داده‌ها (Data Layer)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            دریافت مستقیم تیک‌های GC Futures از بورس CME و داده‌های Spot با رزولوشن میکروثانیه. ذخیره‌سازی ستونی در قالب DuckDB و Parquet جهت تضمین سرعت کوئری فوق‌العاده بالا و پایش دائمی Basis Spread.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-amber-400 mb-3 flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            ۲. لایه جریان سفارشات و فوت‌پرینت (Order Flow Layer)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            محاسبه آنی ماتریس Bid/Ask در هر سطح قیمت با Numba JIT، شناسایی عدم‌تعادل‌های قطری (Diagonal Imbalances &gt; 300%)، پایش دلتا، CVD و جذب لیمیت (Passive Limit Absorption) در سقف‌ها و کف‌ها.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-cyan-400 mb-3 flex items-center gap-2">
            <Network className="w-4 h-4" />
            ۳. لایه ساختار بازار و کانتکست (Market Structure)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            رهگیری استخرهای نقدینگی استاپ خریداران (BSL) و فروشندگان (SSL) در تایم‌فریم‌های ۱۵ دقیقه و ۱ ساعته، مکان‌یابی گپ‌های ارزش منصفانه (FVG) و رژیم‌های فشردگی/انبساط نوسان.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-rose-400 mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            ۴. لایه قرنطینه اخبار کلان (News Quarantine Layer)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            مسدودسازی خودکار صدور سیگنال در پنجره ۱۵ دقیقه قبل تا ۲۰ دقیقه بعد از اعلام داده‌های رده ۱ اقتصادی (CPI, NFP, FOMC) جهت حفاظت در برابر اسپایک‌های غیرقابل پیش‌بینی اسپرد بروکر.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-emerald-400 mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            ۵. لایه داور اکید تصمیم‌گیری (Decision Arbiter)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            فیلتر قطعی تمام سناریوهای مشکوک و تولید خروجی انحصاری <code className="text-amber-300 font-mono font-bold">CALL / PUT / NO TRADE</code> همراه با لاگ توجیهی و بردار توضیح‌پذیری کامل برای هر تصمیم.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
          <h3 className="text-sm font-bold text-purple-400 mb-3 flex items-center gap-2">
            <Award className="w-4 h-4" />
            ۶. لایه بک‌تستینگ و آزمون‌های مونت‌کارلو (Validation Lab)
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            شبیه‌سازی واقع‌گرایانه زمان انقضای ۵ دقیقه‌ای، لحاظ عدم تقارن پی‌اوت بروکرها و اجرای آزمون‌های جایگشت مونت‌کارلو برای تفکیک لبه آماری واقعی از شانس و تصادف.
          </p>
        </div>

      </div>

      {/* Strict Engineering Rules Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <h3 className="text-base font-bold text-slate-100 mb-3 flex items-center gap-2">
          <Terminal className="w-4 h-4 text-amber-400" />
          قوانین حاکمیت مهندسی و اخلاق پژوهش (Engineering Principles)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
            <span className="font-bold text-amber-400 block mb-1">۱. ممنوعیت مطلق سیستم‌های بازیابی (No Martingale/Grid):</span>
            هیچ‌گونه روش تصاعدی، مارتینگل، دو برابر کردن حجم یا میانگین‌کم‌کنی در این سیستم مجاز نبوده و از ریشه فیلتر شده است.
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
            <span className="font-bold text-amber-400 block mb-1">۲. پیش‌فرض روی عدم معامله (Default to NO TRADE):</span>
            در صورت هرگونه ابهام، ناهماهنگی تیک‌ها، عدم تعادل مشکوک یا اسپرد بالا، سیستم بلافاصله خروجی NO TRADE تولید می‌کند.
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
            <span className="font-bold text-amber-400 block mb-1">۳. عدم ساخت داده‌های فیک (Zero Hallucinated Order Flow):</span>
            محاسبات فوت‌پرینت تنها و تنها بر اساس تیک‌های استاندارد Bid/Ask انجام می‌گیرد و هرگز با حجم کندل اسپات شبیه‌سازی جعلی نمی‌شود.
          </div>

          <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-slate-300">
            <span className="font-bold text-amber-400 block mb-1">۴. توضیح‌پذیری ۱۰۰٪ تصمیمات (Full Explainability):</span>
            تمامی دلایل ورود یا وتوی سیگنال همراه با وزن‌های آماری در پایگاه داده ثبت و در داشبورد قابل ردیابی هستند.
          </div>
        </div>
      </div>
    </div>
  );
};
