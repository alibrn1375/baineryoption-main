import React from 'react';
import { ArrowUpRight, ArrowDownRight, Ban, CheckCircle2, XCircle, ShieldCheck, AlertTriangle, Info } from 'lucide-react';
import { SignalDecision } from '../types';

interface LiveArbiterCardProps {
  decision: SignalDecision;
  currentPayout: number;
  onChangePayout: (payout: number) => void;
}

export const LiveArbiterCard: React.FC<LiveArbiterCardProps> = ({
  decision,
  currentPayout,
  onChangePayout,
}) => {
  const isCall = decision.action === 'CALL';
  const isPut = decision.action === 'PUT';
  const isNoTrade = decision.action === 'NO_TRADE';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl relative overflow-hidden">
      {/* Subtle background glow based on action */}
      <div
        className={`absolute -top-24 -left-24 w-64 h-64 rounded-full blur-3xl pointer-events-none opacity-20 ${
          isCall ? 'bg-emerald-500' : isPut ? 'bg-rose-500' : 'bg-amber-500'
        }`}
      />

      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800 relative z-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold text-slate-400">داور تصمیم‌گیرنده اکید (Tri-State Arbiter)</span>
            <span className="bg-slate-800 text-slate-400 text-[10px] px-1.5 py-0.5 rounded font-mono">۵ دقیقه</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mt-1">وضعیت سیگنال کندل جاری</h2>
        </div>

        {/* Broker Payout Simulator Control */}
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <span className="text-slate-400">پی‌اوت بروکر:</span>
          <select
            value={currentPayout}
            onChange={(e) => onChangePayout(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 text-amber-300 font-mono font-bold rounded px-2 py-1 focus:outline-none focus:border-amber-500"
          >
            <option value={0.75}>75% (امید ریاضی منفی - وتو)</option>
            <option value={0.80}>80% (حداقل سر‌به‌سر ۵۵.۵٪)</option>
            <option value={0.85}>85% (استاندارد مطلوب ۶۰٪+)</option>
            <option value={0.90}>90% (عالی)</option>
          </select>
        </div>
      </div>

      {/* Decision Big Display Banner */}
      <div className="my-5 grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        
        {/* Left: Main Action Badge */}
        <div className="md:col-span-1 flex flex-col items-center justify-center p-5 rounded-xl border text-center relative z-10"
          style={{
            backgroundColor: isCall ? 'rgba(16, 185, 129, 0.08)' : isPut ? 'rgba(244, 63, 94, 0.08)' : 'rgba(245, 158, 11, 0.08)',
            borderColor: isCall ? 'rgba(16, 185, 129, 0.3)' : isPut ? 'rgba(244, 63, 94, 0.3)' : 'rgba(245, 158, 11, 0.3)',
          }}
        >
          <div className="text-[11px] font-mono text-slate-400 mb-1">خروجی قطعی سیستم:</div>
          <div className="flex items-center gap-2">
            {isCall && <ArrowUpRight className="w-8 h-8 text-emerald-400" />}
            {isPut && <ArrowDownRight className="w-8 h-8 text-rose-400" />}
            {isNoTrade && <Ban className="w-7 h-7 text-amber-400" />}

            <span
              className={`text-3xl font-black font-mono tracking-wider ${
                isCall ? 'text-emerald-400' : isPut ? 'text-rose-400' : 'text-amber-400'
              }`}
            >
              {decision.action.replace('_', ' ')}
            </span>
          </div>

          <div className="mt-2 text-xs text-slate-300 font-medium max-w-xs">
            {isCall && 'مجوز صدور آپشن خرید ۵ دقیقه‌ای'}
            {isPut && 'مجوز صدور آپشن فروش ۵ دقیقه‌ای'}
            {isNoTrade && 'معامله ممنوع — عدم انطباق شرایط با فرضیه آماری'}
          </div>
        </div>

        {/* Center: Hypothesis & Explainability */}
        <div className="md:col-span-2 bg-slate-950/70 p-4 rounded-xl border border-slate-800/80 flex flex-col justify-between h-full">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span className="font-semibold flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-amber-400" />
                تفسیر منطقی ریزساختار و فرضیه:
              </span>
              <span className="font-mono text-amber-300 font-bold">
                امتیاز اطمینان: {decision.confidenceScore}%
              </span>
            </div>

            <p className="text-sm font-medium text-slate-200 leading-relaxed mb-3">
              {decision.primaryHypothesis}
            </p>
          </div>

          {/* Rejection / Veto Logs */}
          {decision.rejectionReasons.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-2.5 text-xs text-amber-200">
              <div className="flex items-center gap-1.5 font-bold mb-1 text-amber-400">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>فاکتورهای بازدارنده و وتوکننده سیگنال:</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                {decision.rejectionReasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

      </div>

      {/* Checklist Gate Breakdown */}
      <div className="mt-4 pt-4 border-t border-slate-800">
        <h4 className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          چک‌لیست ۵ فاکتور طلایی پیش از مجاز شدن ورود:
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {decision.checklist.map((item, idx) => (
            <div
              key={idx}
              className={`p-2.5 rounded-lg border text-xs flex items-start gap-2.5 transition-all ${
                item.satisfied
                  ? 'bg-emerald-950/20 border-emerald-500/30 text-slate-200'
                  : 'bg-slate-950 border-slate-800/80 text-slate-400'
              }`}
            >
              {item.satisfied ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <XCircle className="w-4 h-4 text-slate-600 shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className={`font-semibold ${item.satisfied ? 'text-emerald-300' : 'text-slate-300'}`}>
                    {item.name}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">وزن: {item.weight}%</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5">{item.details}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
