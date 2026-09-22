import React from 'react';
import { BookOpen, CheckCircle2, XCircle, MinusCircle, Clock, ShieldCheck, TrendingUp, TrendingDown } from 'lucide-react';

export interface PaperTradeRecord {
  id: string;
  timestamp: string;
  symbol: string;
  setup: string;
  decision: 'CALL' | 'PUT' | 'NO_TRADE';
  entryPrice: number;
  expiryPrice: number;
  qualityScore: number;
  winProbability: number;
  expectedValue: number;
  payoutRate: number;
  outcome: 'WIN' | 'LOSS' | 'TIE' | 'REJECTED';
  reasons: string[];
}

interface JournalProps {
  trades?: PaperTradeRecord[];
}

const defaultTrades: PaperTradeRecord[] = [
  {
    id: 'pt-501',
    timestamp: '2026-08-30 14:35:00 UTC',
    symbol: 'GC_FUT',
    setup: '3x Stacked Buy Imbalance + Absorption',
    decision: 'CALL',
    entryPrice: 2646.20,
    expiryPrice: 2647.10,
    qualityScore: 94.0,
    winProbability: 0.76,
    expectedValue: 0.41,
    payoutRate: 0.85,
    outcome: 'WIN',
    reasons: ['انباشت ایمبالانس خریدار در کف ساختار', 'جذب کامل فروشندگان در سطح ۲۶۴۴.۲۰', 'همگرایی دلتای تجمعی']
  },
  {
    id: 'pt-500',
    timestamp: '2026-08-30 14:30:00 UTC',
    symbol: 'GC_FUT',
    setup: 'Low Delta Confluence',
    decision: 'NO_TRADE',
    entryPrice: 2645.80,
    expiryPrice: 2645.90,
    qualityScore: 61.0,
    winProbability: 0.52,
    expectedValue: -0.04,
    payoutRate: 0.85,
    outcome: 'REJECTED',
    reasons: ['امید ریاضی منفی بر اساس نرخ پرداخت ۸۵٪', 'عدم تائید فوت‌پرینت توسط ساختار ۱۵ دقیقه']
  },
  {
    id: 'pt-499',
    timestamp: '2026-08-30 14:25:00 UTC',
    symbol: 'GC_FUT',
    setup: 'Volume Exhaustion + Value Rejection',
    decision: 'PUT',
    entryPrice: 2648.50,
    expiryPrice: 2647.30,
    qualityScore: 89.0,
    winProbability: 0.71,
    expectedValue: 0.31,
    payoutRate: 0.85,
    outcome: 'WIN',
    reasons: ['خستگی حجم در سقف روز', 'چرخش شدید دلتا به سمت منفی (-480)', 'تائید شکست ساختار داخلی']
  },
  {
    id: 'pt-498',
    timestamp: '2026-08-30 14:20:00 UTC',
    symbol: 'GC_FUT',
    setup: 'Trapped Buyers at Resistance',
    decision: 'PUT',
    entryPrice: 2649.10,
    expiryPrice: 2649.30,
    qualityScore: 82.0,
    winProbability: 0.65,
    expectedValue: 0.20,
    payoutRate: 0.85,
    outcome: 'LOSS',
    reasons: ['به دام افتادن خریداران با حجم بالا در سقف', 'ادامه مومنتوم صعودی بازار کلان خلاف ستاپ']
  }
];

export const Journal: React.FC<JournalProps> = ({ trades = defaultTrades }) => {
  const winCount = trades.filter((t) => t.outcome === 'WIN').length;
  const lossCount = trades.filter((t) => t.outcome === 'LOSS').length;
  const totalExecuted = winCount + lossCount;
  const winRate = totalExecuted > 0 ? (winCount / totalExecuted) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-mono">کل ارزیابی‌ها (Evaluations)</div>
          <div className="text-2xl font-black font-mono text-slate-100 mt-1">{trades.length}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-mono">معاملات شبیه‌سازی شده (Executed)</div>
          <div className="text-2xl font-black font-mono text-amber-400 mt-1">{totalExecuted}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-mono">وین‌ریت ۵ دقیقه‌ای (Win Rate)</div>
          <div className={`text-2xl font-black font-mono mt-1 ${winRate >= 60 ? 'text-emerald-400' : 'text-slate-200'}`}>
            {winRate.toFixed(1)}%
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="text-xs text-slate-400 font-mono">نسبت برد/باخت (W / L / Rejected)</div>
          <div className="text-sm font-bold font-mono text-slate-300 mt-2 flex items-center gap-2">
            <span className="text-emerald-400">{winCount}W</span>
            <span>/</span>
            <span className="text-rose-400">{lossCount}L</span>
            <span>/</span>
            <span className="text-slate-500">{trades.length - totalExecuted} NoTrade</span>
          </div>
        </div>
      </div>

      {/* Trade Journal Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-slate-100 font-mono uppercase">
              FO-X 5M Quantitative Trade Journal & Audit Log
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Paper Trading Execution Simulator</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-right text-xs font-mono">
            <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="p-3 text-right">شناسه / زمان</th>
                <th className="p-3 text-right">نماد و ستاپ</th>
                <th className="p-3 text-center">سیگنال سه‌حالته</th>
                <th className="p-3 text-center">ورود / انقضا</th>
                <th className="p-3 text-center">کیفیت / احتمال برد</th>
                <th className="p-3 text-center">EV (امید ریاضی)</th>
                <th className="p-3 text-center">نتیجه</th>
                <th className="p-3 text-right">دلایل تصمیم و ابطال</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {trades.map((trade) => (
                <tr key={trade.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="p-3 whitespace-nowrap">
                    <div className="text-slate-200 font-bold">{trade.id}</div>
                    <div className="text-[10px] text-slate-500">{trade.timestamp}</div>
                  </td>
                  <td className="p-3">
                    <div className="text-amber-400 font-semibold">{trade.symbol}</div>
                    <div className="text-[11px] text-slate-400">{trade.setup}</div>
                  </td>
                  <td className="p-3 text-center">
                    {trade.decision === 'CALL' && (
                      <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-bold">
                        <TrendingUp className="w-3 h-3" /> CALL
                      </span>
                    )}
                    {trade.decision === 'PUT' && (
                      <span className="inline-flex items-center gap-1 bg-rose-500/10 text-rose-400 border border-rose-500/30 px-2 py-0.5 rounded font-bold">
                        <TrendingDown className="w-3 h-3" /> PUT
                      </span>
                    )}
                    {trade.decision === 'NO_TRADE' && (
                      <span className="inline-flex items-center gap-1 bg-slate-800 text-slate-400 border border-slate-700 px-2 py-0.5 rounded font-bold">
                        <MinusCircle className="w-3 h-3" /> NO TRADE
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-center whitespace-nowrap text-slate-300">
                    <div>{trade.entryPrice.toFixed(2)} &rarr; {trade.expiryPrice.toFixed(2)}</div>
                  </td>
                  <td className="p-3 text-center whitespace-nowrap">
                    <div className="text-slate-200 font-bold">{(trade.winProbability * 100).toFixed(0)}%</div>
                    <div className="text-[10px] text-slate-400">QS: {trade.qualityScore}</div>
                  </td>
                  <td className="p-3 text-center">
                    <span className={`font-bold ${trade.expectedValue > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
                      {trade.expectedValue > 0 ? `+${trade.expectedValue.toFixed(2)}` : trade.expectedValue.toFixed(2)}
                    </span>
                  </td>
                  <td className="p-3 text-center">
                    {trade.outcome === 'WIN' && (
                      <span className="inline-flex items-center gap-1 text-emerald-400 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        <CheckCircle2 className="w-3 h-3" /> WIN
                      </span>
                    )}
                    {trade.outcome === 'LOSS' && (
                      <span className="inline-flex items-center gap-1 text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                        <XCircle className="w-3 h-3" /> LOSS
                      </span>
                    )}
                    {trade.outcome === 'REJECTED' && (
                      <span className="inline-flex items-center gap-1 text-slate-400 font-bold bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                        REJECTED
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-[11px] text-slate-400 max-w-xs">
                    <ul className="list-disc list-inside space-y-0.5">
                      {trade.reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
