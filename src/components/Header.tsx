import React from 'react';
import { Activity, Code, Database, Radio, RefreshCw, ShieldAlert, Cpu, Sparkles } from 'lucide-react';

interface HeaderProps {
  isLiveStream: boolean;
  onToggleLiveStream: () => void;
  secondsRemaining: number;
  gcPrice: number;
  spotPrice: number;
  onOpenPythonModal: () => void;
  onOpenDataModal: () => void;
  activeTab: 'terminal' | 'journal' | 'analytics' | 'pipeline' | 'intelligence' | 'context' | 'decision' | 'backtest' | 'architecture';
  setActiveTab: (tab: 'terminal' | 'journal' | 'analytics' | 'pipeline' | 'intelligence' | 'context' | 'decision' | 'backtest' | 'architecture') => void;
}

export const Header: React.FC<HeaderProps> = ({
  isLiveStream,
  onToggleLiveStream,
  secondsRemaining,
  gcPrice,
  spotPrice,
  onOpenPythonModal,
  onOpenDataModal,
  activeTab,
  setActiveTab,
}) => {
  const basis = Number((gcPrice - spotPrice).toFixed(2));
  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 sticky top-0 z-40 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        
        {/* Left: Branding & Core Mode */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-lg shadow-inner">
              <Cpu className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold tracking-wider text-slate-100 font-mono text-base">FO-X 5M</span>
                <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] px-1.5 py-0.5 rounded font-mono font-medium">
                  GC &times; XAU/USD
                </span>
                <span className="bg-slate-800 text-slate-400 border border-slate-700 text-[10px] px-1.5 py-0.5 rounded font-mono">
                  v1.0-QUANT
                </span>
              </div>
              <p className="text-[12px] text-slate-400">موتور تحقیقاتی ریزساختار و جریان سفارشات ۵ دقیقه‌ای طلا</p>
            </div>
          </div>

          {/* Quick Tab Switcher */}
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
            <button
              onClick={() => setActiveTab('terminal')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'terminal'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ترمینال زنده (5M)
            </button>
            <button
              onClick={() => setActiveTab('journal')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'journal'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ژورنال معاملات (Phase 16)
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'analytics'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              آنالیتیکس و مونت‌کارلو
            </button>
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'pipeline'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              پایپ‌لاین داده و فوت‌پرینت (Phase 1)
            </button>
            <button
              onClick={() => setActiveTab('intelligence')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'intelligence'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              هوشمندی اردر فلو (Phase 2)
            </button>
            <button
              onClick={() => setActiveTab('context')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'context'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              بافتار بازار و ریسک (Phase 3)
            </button>
            <button
              onClick={() => setActiveTab('decision')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'decision'
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              موتور ستاپ و تصمیم‌گیری (Phase 4)
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'backtest'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              لَب بک‌تستینگ و مونت‌کارلو
            </button>
            <button
              onClick={() => setActiveTab('architecture')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                activeTab === 'architecture'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              معماری و متدولوژی
            </button>
          </div>
        </div>

        {/* Right: Metrics, Live Feeds, Exporters */}
        <div className="flex items-center flex-wrap gap-2.5 w-full md:w-auto justify-end">
          
          {/* Basis Monitor (GC vs Spot) */}
          <div className="bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800/80 flex items-center gap-3 text-xs font-mono">
            <div>
              <span className="text-slate-500 text-[10px] block">GC فیوچرز:</span>
              <span className="text-amber-300 font-semibold">${gcPrice.toFixed(1)}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 text-[10px] block">XAU اسپات:</span>
              <span className="text-slate-200 font-semibold">${spotPrice.toFixed(1)}</span>
            </div>
            <div className="h-6 w-px bg-slate-800" />
            <div>
              <span className="text-slate-500 text-[10px] block">Basis Spread:</span>
              <span className={`font-semibold ${Math.abs(basis) > 1.5 ? 'text-rose-400' : 'text-emerald-400'}`}>
                ${basis >= 0 ? `+${basis}` : basis}
              </span>
            </div>
          </div>

          {/* 5M Countdown Timer */}
          <div className="bg-slate-950/80 px-2.5 py-1.5 rounded-lg border border-slate-800 flex items-center gap-2 text-xs font-mono">
            <Activity className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
            <div>
              <span className="text-slate-500 text-[10px] block">انقضای کندل 5M:</span>
              <span className="text-amber-400 font-bold">{formatSeconds(secondsRemaining)}</span>
            </div>
          </div>

          {/* Live Feed Toggle */}
          <button
            onClick={onToggleLiveStream}
            className={`px-3 py-1.5 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-all ${
              isLiveStream
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/20'
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="شبیه‌سازی جریان زنده تیک‌ها"
          >
            <Radio className={`w-3.5 h-3.5 ${isLiveStream ? 'animate-pulse text-emerald-400' : ''}`} />
            <span>{isLiveStream ? 'استریم زنده تیک فعال' : 'استریم تیک متوقف'}</span>
          </button>

          {/* Data Inspector Button */}
          <button
            onClick={onOpenDataModal}
            className="px-2.5 py-1.5 bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all"
            title="مشاهده تیک‌های خام و پایگاه داده"
          >
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">داده‌ها</span>
          </button>

          {/* Python Code Export */}
          <button
            onClick={onOpenPythonModal}
            className="px-3 py-1.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-slate-950 font-bold rounded-lg text-xs flex items-center gap-1.5 transition-all shadow-md shadow-amber-500/10"
            title="مشاهده و دانلود کدهای پایتون"
          >
            <Code className="w-3.5 h-3.5" />
            <span>کد پایتون</span>
          </button>

        </div>
      </div>
    </header>
  );
};
