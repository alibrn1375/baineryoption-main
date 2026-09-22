import React, { useState } from 'react';
import { FootprintBar } from '../types';
import { BarChart3, Flame, Layers, ShieldCheck, Target, Zap } from 'lucide-react';

interface FootprintViewerProps {
  bars: FootprintBar[];
  selectedBarId: string;
  onSelectBar: (barId: string) => void;
}

export const FootprintViewer: React.FC<FootprintViewerProps> = ({
  bars,
  selectedBarId,
  onSelectBar,
}) => {
  const [viewMode, setViewMode] = useState<'footprint' | 'profile' | 'delta'>('footprint');
  const selectedBar = bars.find((b) => b.id === selectedBarId) || bars[bars.length - 1];

  // Find max volume in selected bar for proportional heatmaps
  const maxLvlVol = Math.max(...selectedBar.priceLevels.map((l) => l.totalVolume), 1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      {/* Top Controls & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold text-amber-400">لایه ۲ — ریزساختار فوت‌پرینت (Footprint 5M)</span>
            <span className="bg-slate-800 text-slate-400 text-[10px] px-1.5 py-0.5 rounded font-mono">
              تایم‌فریم: ۵ دقیقه
            </span>
          </div>
          <h3 className="text-lg font-bold text-slate-100 mt-0.5">تحلیل ماتریسی Bid/Ask و توزیع دلتا</h3>
        </div>

        {/* View Mode Toggle */}
        <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
          <button
            onClick={() => setViewMode('footprint')}
            className={`px-2.5 py-1 rounded transition-all ${
              viewMode === 'footprint' ? 'bg-amber-500/20 text-amber-300 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            نردبان Bid &times; Ask
          </button>
          <button
            onClick={() => setViewMode('profile')}
            className={`px-2.5 py-1 rounded transition-all ${
              viewMode === 'profile' ? 'bg-amber-500/20 text-amber-300 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            پروفایل حجم و ارزش (VA)
          </button>
        </div>
      </div>

      {/* 5-Minute Candle Bar Selector Ribbon */}
      <div className="my-4 flex items-center gap-2 overflow-x-auto pb-2">
        <span className="text-xs text-slate-400 font-mono shrink-0">کندل‌های ۵M:</span>
        {bars.map((bar) => {
          const isSelected = bar.id === selectedBar.id;
          const isBullish = bar.close >= bar.open;
          return (
            <button
              key={bar.id}
              onClick={() => onSelectBar(bar.id)}
              className={`px-3 py-2 rounded-lg border text-xs font-mono flex flex-col items-center transition-all shrink-0 ${
                isSelected
                  ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-md'
                  : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-400'
              }`}
            >
              <span className="font-bold">{bar.time}</span>
              <span className={`text-[11px] font-semibold ${isBullish ? 'text-emerald-400' : 'text-rose-400'}`}>
                ${bar.close.toFixed(1)}
              </span>
              <span className={`text-[10px] ${bar.delta >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                Δ {bar.delta >= 0 ? `+${bar.delta}` : bar.delta}
              </span>
            </button>
          );
        })}
      </div>

      {/* Selected Bar Microstructure Meta Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/70 p-3 rounded-lg border border-slate-800/80 mb-4 text-xs font-mono">
        <div>
          <span className="text-slate-500 text-[10px] block">POC (بیشترین حجم):</span>
          <span className="text-amber-400 font-bold text-sm">${selectedBar.pocPrice.toFixed(1)}</span>
        </div>
        <div>
          <span className="text-slate-500 text-[10px] block">Value Area (70%):</span>
          <span className="text-slate-200 font-semibold text-sm">
            ${selectedBar.val.toFixed(1)} — ${selectedBar.vah.toFixed(1)}
          </span>
        </div>
        <div>
          <span className="text-slate-500 text-[10px] block">دلتای خالص کندل:</span>
          <span className={`font-bold text-sm ${selectedBar.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {selectedBar.delta >= 0 ? `+${selectedBar.delta}` : selectedBar.delta}
          </span>
        </div>
        <div>
          <span className="text-slate-500 text-[10px] block">CVD تجمعی:</span>
          <span className="text-cyan-400 font-bold text-sm">{selectedBar.cvd}</span>
        </div>
      </div>

      {/* Footprint Price Ladder Matrix Display */}
      <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950 font-mono">
        <div className="grid grid-cols-12 bg-slate-900/90 py-2 px-3 text-[11px] font-bold text-slate-400 border-b border-slate-800">
          <div className="col-span-3 text-right">قیمت (Gold GC)</div>
          <div className="col-span-3 text-center text-rose-400">Bid Vol (فروش مارکت)</div>
          <div className="col-span-1 text-center text-slate-600">&times;</div>
          <div className="col-span-3 text-center text-emerald-400">Ask Vol (خرید مارکت)</div>
          <div className="col-span-2 text-left">دلتا / پدیده‌ها</div>
        </div>

        <div className="divide-y divide-slate-900 max-h-[360px] overflow-y-auto">
          {selectedBar.priceLevels
            .slice()
            .reverse()
            .map((lvl) => {
              const isPoc = lvl.price === selectedBar.pocPrice;
              const isValueArea = lvl.price >= selectedBar.val && lvl.price <= selectedBar.vah;
              const bidRatio = lvl.bidVolume / maxLvlVol;
              const askRatio = lvl.askVolume / maxLvlVol;

              return (
                <div
                  key={lvl.price}
                  className={`grid grid-cols-12 py-1.5 px-3 text-xs items-center transition-colors hover:bg-slate-800/40 ${
                    isPoc
                      ? 'bg-amber-500/10 font-bold border-y border-amber-500/30'
                      : isValueArea
                      ? 'bg-slate-900/40'
                      : ''
                  }`}
                >
                  {/* Price Level */}
                  <div className="col-span-3 flex items-center gap-1.5">
                    <span className={isPoc ? 'text-amber-300 font-extrabold' : 'text-slate-300'}>
                      ${lvl.price.toFixed(1)}
                    </span>
                    {isPoc && (
                      <span className="bg-amber-500 text-slate-950 text-[9px] px-1 rounded font-black">POC</span>
                    )}
                  </div>

                  {/* Bid Volume with Relative Heatmap Bar */}
                  <div className="col-span-3 relative text-center">
                    <div
                      className="absolute inset-y-0 right-0 bg-rose-500/15 rounded-sm pointer-events-none"
                      style={{ width: `${Math.min(100, bidRatio * 100)}%` }}
                    />
                    <span
                      className={`relative z-10 font-medium ${
                        lvl.bidImbalance ? 'text-rose-300 font-extrabold underline decoration-rose-500' : 'text-rose-400'
                      }`}
                    >
                      {lvl.bidVolume}
                    </span>
                  </div>

                  <div className="col-span-1 text-center text-slate-700 text-[10px]">&times;</div>

                  {/* Ask Volume with Relative Heatmap Bar */}
                  <div className="col-span-3 relative text-center">
                    <div
                      className="absolute inset-y-0 left-0 bg-emerald-500/15 rounded-sm pointer-events-none"
                      style={{ width: `${Math.min(100, askRatio * 100)}%` }}
                    />
                    <span
                      className={`relative z-10 font-medium ${
                        lvl.askImbalance
                          ? 'text-emerald-300 font-extrabold underline decoration-emerald-500'
                          : 'text-emerald-400'
                      }`}
                    >
                      {lvl.askVolume}
                    </span>
                  </div>

                  {/* Delta & Microstructure Badges */}
                  <div className="col-span-2 flex items-center justify-end gap-1.5 text-[10px]">
                    <span className={lvl.delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                      {lvl.delta >= 0 ? `+${lvl.delta}` : lvl.delta}
                    </span>

                    {lvl.isAbsorption && (
                      <span
                        className="bg-purple-500/20 text-purple-300 border border-purple-500/40 px-1 rounded font-bold"
                        title="Passive Absorption Node"
                      >
                        ABS
                      </span>
                    )}

                    {lvl.askImbalance && (
                      <span
                        className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-1 rounded font-bold"
                        title="Aggressive Buyer Imbalance (Ask > 3x Bid)"
                      >
                        IMB+
                      </span>
                    )}

                    {lvl.bidImbalance && (
                      <span
                        className="bg-rose-500/20 text-rose-300 border border-rose-500/40 px-1 rounded font-bold"
                        title="Aggressive Seller Imbalance (Bid > 3x Ask)"
                      >
                        IMB-
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Order Flow Legend */}
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span>POC = بیشترین حجم معامله</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>IMB+ = عدم‌تعادل تهاجمی خرید</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-400" />
            <span>IMB- = عدم‌تعادل تهاجمی فروش</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-400" />
            <span>ABS = جذب حجم لیمیت (Passive Iceberg)</span>
          </span>
        </div>
      </div>
    </div>
  );
};
