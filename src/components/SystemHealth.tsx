import React from 'react';
import { Activity, ShieldCheck, Wifi, WifiOff, AlertTriangle, Clock, Zap } from 'lucide-react';

interface SystemHealthProps {
  latencyMs: number;
  provider: string;
  connectionState: 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';
  qualityScore: number;
  processedTicksCount: number;
  lastMessageTime: string;
}

export const SystemHealth: React.FC<SystemHealthProps> = ({
  latencyMs,
  provider,
  connectionState,
  qualityScore,
  processedTicksCount,
  lastMessageTime,
}) => {
  const isHealthy = connectionState === 'CONNECTED' && qualityScore >= 90;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-slate-200 tracking-wider uppercase font-mono">
            System Health & Telemetry Monitor
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          {connectionState === 'CONNECTED' ? (
            <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded">
              <Wifi className="w-3 h-3" /> ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] font-mono text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded">
              <WifiOff className="w-3 h-3" /> OFFLINE
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
          <div className="text-[10px] text-slate-500 font-mono mb-1">DATA PROVIDER</div>
          <div className="text-xs font-bold font-mono text-amber-400 flex items-center gap-1">
            <Zap className="w-3 h-3 text-amber-400" />
            {provider}
          </div>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
          <div className="text-[10px] text-slate-500 font-mono mb-1">FEED LATENCY</div>
          <div className={`text-xs font-bold font-mono ${latencyMs > 100 ? 'text-rose-400' : 'text-emerald-400'}`}>
            {latencyMs.toFixed(1)} ms
          </div>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
          <div className="text-[10px] text-slate-500 font-mono mb-1">QUALITY SCORE</div>
          <div className={`text-xs font-bold font-mono flex items-center gap-1 ${qualityScore < 85 ? 'text-amber-400' : 'text-cyan-400'}`}>
            <ShieldCheck className="w-3 h-3" />
            {qualityScore.toFixed(1)} / 100
          </div>
        </div>

        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
          <div className="text-[10px] text-slate-500 font-mono mb-1">PROCESSED TICKS</div>
          <div className="text-xs font-bold font-mono text-slate-200">
            {processedTicksCount.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-500">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-slate-500" />
          <span>آخرین هارت‌بیت: {lastMessageTime}</span>
        </div>
        <div className="flex items-center gap-1">
          <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-amber-500'}`} />
          <span className="text-slate-400">{isHealthy ? 'تغذیه داده نرمال و پایدار' : 'هشدار در سلامت فید داده'}</span>
        </div>
      </div>
    </div>
  );
};
