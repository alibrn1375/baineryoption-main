import React from 'react';
import { MarketStructure } from '../types';
import { Compass, Crosshair, Layers, TrendingDown, TrendingUp, Waves } from 'lucide-react';

interface MarketStructurePanelProps {
  structure15M: MarketStructure;
  structure1H: MarketStructure;
  currentPrice: number;
}

export const MarketStructurePanel: React.FC<MarketStructurePanelProps> = ({
  structure15M,
  structure1H,
  currentPrice,
}) => {
  const distToSsl15 = Math.abs(currentPrice - structure15M.sslPrice).toFixed(1);
  const distToBsl15 = Math.abs(currentPrice - structure15M.bslPrice).toFixed(1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-cyan-400">لایه ۳ — ساختار بازار و کانتکست (HTF Context)</span>
          <span className="bg-slate-800 text-slate-400 text-[10px] px-1.5 py-0.5 rounded font-mono">15M / 1H</span>
        </div>
        <Compass className="w-4 h-4 text-cyan-400" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        
        {/* 15M Structure Box */}
        <div className="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-xs mb-2.5">
            <span className="font-bold text-slate-300 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              تایم‌فریم ۱۵ دقیقه (تصمیم‌گیری میانی)
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${
                structure15M.trend === 'BULLISH'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              {structure15M.trend === 'BULLISH' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {structure15M.trend === 'BULLISH' ? 'روند صعودی' : 'روند نزولی'}
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded">
              <span className="text-slate-400">BSL (نقدینگی سقف):</span>
              <div className="text-right">
                <span className="text-rose-400 font-bold">${structure15M.bslPrice.toFixed(1)}</span>
                <span className="text-[10px] text-slate-500 block">فاصله: {distToBsl15}$</span>
              </div>
            </div>

            <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded">
              <span className="text-slate-400">SSL (نقدینگی کف):</span>
              <div className="text-right">
                <span className="text-emerald-400 font-bold">${structure15M.sslPrice.toFixed(1)}</span>
                <span className="text-[10px] text-slate-500 block">فاصله: {distToSsl15}$</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>رژیم نوسان (ATR):</span>
              <span className="text-slate-200 font-bold">${structure15M.atr.toFixed(1)} (نرمال)</span>
            </div>
          </div>
        </div>

        {/* 1H Macro Structure Box */}
        <div className="bg-slate-950/70 p-3.5 rounded-lg border border-slate-800/80">
          <div className="flex items-center justify-between text-xs mb-2.5">
            <span className="font-bold text-slate-300 flex items-center gap-1.5">
              <Crosshair className="w-3.5 h-3.5 text-cyan-400" />
              تایم‌فریم ۱ ساعته (کانتکست ماژور)
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 ${
                structure1H.trend === 'BULLISH'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
              }`}
            >
              <TrendingUp className="w-3 h-3" />
              روند صعودی ماژور
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded">
              <span className="text-slate-400">BSL ماژور (سقف هفته):</span>
              <span className="text-rose-400 font-bold">${structure1H.bslPrice.toFixed(1)}</span>
            </div>

            <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded">
              <span className="text-slate-400">SSL ماژور (کف هفته):</span>
              <span className="text-emerald-400 font-bold">${structure1H.sslPrice.toFixed(1)}</span>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>شاخص ATR ساعتی:</span>
              <span className="text-slate-200 font-bold">${structure1H.atr.toFixed(1)}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
