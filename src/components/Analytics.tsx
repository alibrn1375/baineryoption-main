import React from 'react';
import { BarChart3, TrendingUp, ShieldAlert, Cpu, PieChart, CheckCircle, Flame } from 'lucide-react';

export const Analytics: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Top Statistical Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>میانگین امید ریاضی (EV)</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black font-mono text-emerald-400 mt-2">+0.28 R</div>
          <div className="text-[11px] text-slate-500 mt-1">با فرض Payout=85% و اسپرد واقعی</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>نرخ پایداری والک فوروارد</span>
            <Cpu className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-black font-mono text-cyan-400 mt-2">84.2%</div>
          <div className="text-[11px] text-slate-500 mt-1">Walk-Forward Efficiency (WFE)</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>حداکثر افت سرمایه (Max DD)</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-black font-mono text-rose-400 mt-2">-4.8%</div>
          <div className="text-[11px] text-slate-500 mt-1">بدترین سناریو مونت‌کارلو 99th %</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>پرافت فاکتور (Profit Factor)</span>
            <Flame className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black font-mono text-amber-400 mt-2">1.88</div>
          <div className="text-[11px] text-slate-500 mt-1">بر روی ۳,۴۵۰ کندل آزمون گذشته‌نگر</div>
        </div>
      </div>

      {/* Detailed Monte Carlo & Setup Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monte Carlo Percentiles */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-slate-100 font-mono uppercase">
                شبیه‌سازی ۵,۰۰۰ گره مونت‌کارلو (Monte Carlo Simulation)
              </h3>
            </div>
            <span className="text-xs text-emerald-400 font-mono font-semibold">10,000 Iterations</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400">بهترین ۱۰٪ سناریوها (90th Percentile Win Rate):</span>
              <span className="text-emerald-400 font-bold">78.4% (EV: +0.45)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400">سناریوی میانه (Median Scenario 50th):</span>
              <span className="text-amber-300 font-bold">68.2% (EV: +0.26)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400">بدترین ۱۰٪ سناریوها (10th Percentile):</span>
              <span className="text-slate-300 font-bold">61.5% (EV: +0.14)</span>
            </div>
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-rose-950/20 border border-rose-900/40">
              <span className="text-rose-400">بدترین ۱٪ سناریوها (Worst 1% Tail Risk):</span>
              <span className="text-rose-300 font-bold">56.2% (Max Losing Streak: 4)</span>
            </div>
          </div>
        </div>

        {/* Setup Distribution & Hit Rate */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-slate-100 font-mono uppercase">
                توزیع عملکرد ستاپ‌های اردر فلو
              </h3>
            </div>
            <span className="text-xs text-cyan-400 font-mono">Out-of-Sample Results</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-slate-200 font-bold">3x Stacked Imbalance + Absorption</div>
                <div className="text-[11px] text-slate-500">تعداد سگنال: ۴۵۰ &bull; میانگین Payout: 85%</div>
              </div>
              <div className="text-right">
                <div className="text-emerald-400 font-bold text-sm">73.8% Win Rate</div>
                <div className="text-[11px] text-emerald-500/80">EV: +0.36</div>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-slate-200 font-bold">Volume Exhaustion at Key Boundary</div>
                <div className="text-[11px] text-slate-500">تعداد سیگنال: ۲۸۰ &bull; میانگین Payout: 85%</div>
              </div>
              <div className="text-right">
                <div className="text-emerald-400 font-bold text-sm">69.4% Win Rate</div>
                <div className="text-[11px] text-emerald-500/80">EV: +0.28</div>
              </div>
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <div className="text-slate-200 font-bold">Trapped Traders + Delta Divergence</div>
                <div className="text-[11px] text-slate-500">تعداد سیگنال: ۳۱۰ &bull; میانگین Payout: 85%</div>
              </div>
              <div className="text-right">
                <div className="text-cyan-400 font-bold text-sm">66.1% Win Rate</div>
                <div className="text-[11px] text-cyan-500/80">EV: +0.22</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
