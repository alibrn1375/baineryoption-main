import React from 'react';
import { NewsEvent } from '../types';
import { AlertOctagon, Calendar, Clock, ShieldCheck, Zap } from 'lucide-react';

interface NewsQuarantinePanelProps {
  newsEvents: NewsEvent[];
  isQuarantineActive: boolean;
}

export const NewsQuarantinePanel: React.FC<NewsQuarantinePanelProps> = ({
  newsEvents,
  isQuarantineActive,
}) => {
  const now = Date.now();

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold text-rose-400">لایه ۴ — فیلتر قرنطینه اخبار کلان (Macro Quarantine)</span>
          <span className="bg-slate-800 text-slate-400 text-[10px] px-1.5 py-0.5 rounded font-mono">Tier-1 News</span>
        </div>
        <Calendar className="w-4 h-4 text-rose-400" />
      </div>

      {/* Status Warning Banner */}
      <div
        className={`my-3 p-3 rounded-lg border text-xs flex items-center justify-between ${
          isQuarantineActive
            ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        }`}
      >
        <div className="flex items-center gap-2">
          {isQuarantineActive ? (
            <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          )}
          <span className="font-bold">
            {isQuarantineActive
              ? 'هشدار: پنجره قرنطینه خبر فعال است — تمامی سیگنال‌ها وتو و NO TRADE هستند'
              : 'وضعیت نرمال: هیچ رویداد کلان بحرانی در بازه زمانی ۱۵ دقیقه قبل و ۲۰ دقیقه بعد وجود ندارد'}
          </span>
        </div>
      </div>

      {/* Events List */}
      <div className="space-y-2 mt-3">
        {newsEvents.map((event) => {
          const diffMinutes = Math.round((event.scheduledTime - now) / (1000 * 60));
          const isPassed = diffMinutes < -event.quarantineMinutesAfter;
          const isInQuarantine = diffMinutes >= -event.quarantineMinutesAfter && diffMinutes <= event.quarantineMinutesBefore;

          return (
            <div
              key={event.id}
              className={`p-3 rounded-lg border text-xs flex items-center justify-between transition-all ${
                isInQuarantine
                  ? 'bg-rose-950/30 border-rose-500/40 text-slate-200'
                  : 'bg-slate-950/70 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="bg-rose-500/20 text-rose-400 font-bold px-2 py-0.5 rounded text-[10px] font-mono">
                  {event.currency} {event.impact}
                </span>
                <div>
                  <div className="font-bold text-slate-200">{event.name}</div>
                  <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                    قرنطینه: {event.quarantineMinutesBefore}m قبل / {event.quarantineMinutesAfter}m بعد
                  </div>
                </div>
              </div>

              <div className="text-left font-mono">
                {isInQuarantine && (
                  <span className="text-rose-400 font-bold text-xs bg-rose-500/20 px-2 py-0.5 rounded border border-rose-500/30">
                    قفل قرنطینه فعال
                  </span>
                )}
                {!isInQuarantine && diffMinutes > 0 && (
                  <span className="text-amber-400 text-xs flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {diffMinutes} دقیقه مانده
                  </span>
                )}
                {isPassed && (
                  <span className="text-slate-500 text-[11px]">پایان یافته</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
