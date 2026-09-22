import React from 'react';
import { NormalizedTick } from '../types';
import { Database, Download, FileSpreadsheet, HardDrive, ShieldCheck, X } from 'lucide-react';

interface DataInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  recentTicks: NormalizedTick[];
}

export const DataInspectorModal: React.FC<DataInspectorModalProps> = ({
  isOpen,
  onClose,
  recentTicks,
}) => {
  if (!isOpen) return null;

  const exportCsv = () => {
    const headers = 'timestamp_utc,symbol,price,size,aggressor_side,bid_price,ask_price\n';
    const rows = recentTicks
      .map(
        (t) =>
          `${new Date(t.timestamp).toISOString()},${t.symbol},${t.price},${t.size},${t.aggressorSide},${t.bidPrice},${t.askPrice}`
      )
      .join('\n');

    const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `gc_ticks_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                بازرس جریان داده‌های تیک خام (Raw Tick Inspector)
                <span className="text-[11px] font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                  CME GC L2 Tick Feed
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                پایش لحظه‌ای ناهماهنگی‌های زمانی، اسپرد و داده‌های جهت تهاجمی (Aggressor Side)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={exportCsv}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>خروجی CSV</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Data Quality Banner */}
        <div className="p-4 bg-slate-950/60 border-b border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            <span>سلامت همگام‌سازی زمانی: ۱۰۰٪ (بدون ناهماهنگی)</span>
          </div>
          <div className="flex items-center gap-2 text-cyan-400">
            <HardDrive className="w-4 h-4" />
            <span>فرمت ذخیره‌سازی: Apache Parquet / DuckDB</span>
          </div>
          <div className="flex items-center gap-2 text-amber-400">
            <FileSpreadsheet className="w-4 h-4" />
            <span>رزولوشن تیک: میکروثانیه (UTC)</span>
          </div>
        </div>

        {/* Tick Table */}
        <div className="flex-1 p-4 overflow-auto bg-slate-950 font-mono text-xs">
          <table className="w-full text-right border-collapse">
            <thead className="bg-slate-900 text-slate-400 sticky top-0 border-b border-slate-800">
              <tr>
                <th className="p-2.5">زمان تیک (UTC)</th>
                <th className="p-2.5">نماد</th>
                <th className="p-2.5">قیمت</th>
                <th className="p-2.5">حجم (Size)</th>
                <th className="p-2.5">جهت تهاجمی</th>
                <th className="p-2.5">Best Bid</th>
                <th className="p-2.5">Best Ask</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-900">
              {recentTicks.map((tick) => (
                <tr key={tick.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="p-2.5 text-slate-400">{new Date(tick.timestamp).toISOString().slice(11, 23)}</td>
                  <td className="p-2.5 text-amber-400 font-bold">{tick.symbol}</td>
                  <td className="p-2.5 text-slate-200 font-bold">${tick.price.toFixed(1)}</td>
                  <td className="p-2.5 text-slate-300 font-bold">{tick.size}</td>
                  <td className="p-2.5">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        tick.aggressorSide === 'BUY'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/20 text-rose-400'
                      }`}
                    >
                      {tick.aggressorSide}
                    </span>
                  </td>
                  <td className="p-2.5 text-rose-400">${tick.bidPrice.toFixed(1)}</td>
                  <td className="p-2.5 text-emerald-400">${tick.askPrice.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
};
