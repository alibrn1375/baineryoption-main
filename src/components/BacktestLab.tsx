import React, { useState, useMemo, useEffect } from 'react';
import { FootprintBar, MarketStructure, NewsEvent, StrategyConfig } from '../types';
import {
  HistoricalReplayEngine,
  BacktestMetricsEngine,
  SetupAnalyticsEngine,
  WalkForwardValidator,
  MonteCarloEngine,
  ParameterStabilityEngine,
  FailureAnalysisEngine,
  PaperTradingEngine
} from '../services/validationEngineService';
import {
  ArrowUpRight,
  ArrowDownRight,
  Award,
  CheckCircle2,
  DollarSign,
  Play,
  Sliders,
  TrendingUp,
  AlertCircle,
  BarChart2,
  Activity,
  Layers,
  Shuffle,
  Compass,
  AlertTriangle,
  BookOpen,
  Send,
  Timer,
  Cpu,
  RefreshCw
} from 'lucide-react';
import { SetupType } from '../types/decisionFramework';

interface BacktestLabProps {
  bars: FootprintBar[];
  structure15M: MarketStructure;
  structure1H: MarketStructure;
  newsEvents: NewsEvent[];
  config: StrategyConfig;
}

export const BacktestLab: React.FC<BacktestLabProps> = ({
  bars,
  structure15M,
  structure1H,
  newsEvents,
  config
}) => {
  const [activeTab, setActiveTab] = useState<
    | 'overview'
    | 'setups'
    | 'walk_forward'
    | 'monte_carlo'
    | 'parameter_stability'
    | 'failures'
    | 'paper_trading'
    | 'journal'
  >('overview');

  const [brokerPayout, setBrokerPayout] = useState<number>(85);
  const [stakeAmount, setStakeAmount] = useState<number>(100);
  const [mcSimCount, setMcSimCount] = useState<number>(1000);
  const [selectedSetup, setSelectedSetup] = useState<SetupType>('SETUP_A_SWEEP_ABSORPTION_REVERSAL');

  // Paper Trading Engine State
  const [paperEngine] = useState(() => new PaperTradingEngine());
  const [paperState, setPaperState] = useState(() => paperEngine.getState());

  // Execute Replay Pipeline
  const { trades, events, researchJournal } = useMemo(() => {
    const replayEngine = new HistoricalReplayEngine();
    return replayEngine.runReplay(bars, brokerPayout, stakeAmount);
  }, [bars, brokerPayout, stakeAmount]);

  // Performance Metrics
  const report = useMemo(() => {
    const metricsEngine = new BacktestMetricsEngine();
    return metricsEngine.calculateMetrics(trades, bars.length, brokerPayout);
  }, [trades, bars.length, brokerPayout]);

  // Setup Analytics
  const setupSummaries = useMemo(() => {
    const setupEngine = new SetupAnalyticsEngine();
    return setupEngine.analyzeSetups(trades);
  }, [trades]);

  // Walk-Forward Validation
  const walkForwardReport = useMemo(() => {
    const wfValidator = new WalkForwardValidator();
    return wfValidator.executeWalkForward(trades);
  }, [trades]);

  // Monte Carlo Simulation
  const [mcResult, setMcResult] = useState(() => {
    const mc = new MonteCarloEngine();
    return mc.runSimulation(trades, mcSimCount, brokerPayout, stakeAmount);
  });

  const handleRunMonteCarlo = () => {
    const mc = new MonteCarloEngine();
    setMcResult(mc.runSimulation(trades, mcSimCount, brokerPayout, stakeAmount));
  };

  // Parameter Stability
  const parameterAnalyses = useMemo(() => {
    const paramEngine = new ParameterStabilityEngine();
    return paramEngine.analyzeParameters();
  }, []);

  // Failure Analysis
  const failureRecords = useMemo(() => {
    const failureEngine = new FailureAnalysisEngine();
    return failureEngine.analyzeFailures(trades);
  }, [trades]);

  // Tick simulation for Paper Trading
  useEffect(() => {
    const interval = setInterval(() => {
      const currentPrice = bars[bars.length - 1]?.close || 2650.0;
      const updated = paperEngine.tickUpdate(currentPrice);
      setPaperState({ ...updated });
    }, 1000);
    return () => clearInterval(interval);
  }, [bars, paperEngine]);

  const winRateDelta = Number((report.basic.winRate - report.binary.breakevenWinRateRequired).toFixed(1));
  const isProfitable = (report.trades[report.trades.length - 1]?.cumulativeProfitUsd || 0) > 0;

  return (
    <div className="space-y-6">
      {/* Top Header & Simulation Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold text-cyan-400">
                فاز ۵ — موتور اعتبارسنجی آماری، بک‌تستینگ و پیپر تریدینگ (Validation & Paper Engine)
              </span>
              <span className="bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-[10px] px-2 py-0.5 rounded font-mono font-bold">
                Zero Look-Ahead Enforcer
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-100 mt-1">
              محیط اعتبارسنجی کمّی، تحلیل مونت‌کارلو (Monte Carlo) و معاملات مجازی
            </h2>
          </div>

          {/* Broker Payout & Stake Settings */}
          <div className="flex flex-wrap items-center gap-4 bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs font-mono">
            <div className="flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-slate-400">پی‌اوت بروکر:</span>
              <span className="text-cyan-400 font-bold">{brokerPayout}%</span>
            </div>
            <input
              type="range"
              min="70"
              max="95"
              step="5"
              value={brokerPayout}
              onChange={(e) => setBrokerPayout(Number(e.target.value))}
              className="w-24 accent-cyan-500 cursor-pointer"
            />
            <div className="flex items-center gap-2 border-r border-slate-800 pr-3">
              <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">استیک:</span>
              <span className="text-emerald-400 font-bold">${stakeAmount}</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1.5 mt-4 overflow-x-auto pb-1 text-xs font-mono">
          {[
            { id: 'overview', label: 'مرور کلی و شاخص‌ها (Overview)', icon: Activity },
            { id: 'setups', label: 'تفکیک ستاپ‌ها (Setup Analytics)', icon: Layers },
            { id: 'walk_forward', label: 'اعتبارسنجی Walk-Forward', icon: Compass },
            { id: 'monte_carlo', label: 'مونت‌کارلو (Monte Carlo)', icon: Shuffle },
            { id: 'parameter_stability', label: 'پایداری پارامترها (Stability)', icon: Sliders },
            { id: 'failures', label: 'ریشه‌یابی خطاها (Failure EDA)', icon: AlertTriangle },
            { id: 'paper_trading', label: 'پیپر تریدینگ زنده (Paper Trading)', icon: Cpu },
            { id: 'journal', label: 'دفترچه ثبت پژوهش (Journal)', icon: BookOpen }
          ].map((tab) => {
            const Icon = tab.icon;
            const isSel = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg font-bold transition-all whitespace-nowrap ${
                  isSel
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* --- TAB 1: OVERVIEW & EQUITY CURVE --- */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metrics 6-Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Win Rate */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">نرخ برد واقعی (Win Rate):</span>
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className="text-2xl font-black text-slate-100 font-mono">{report.basic.winRate}%</span>
                <span className={`text-xs font-mono font-bold ${winRateDelta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ({winRateDelta >= 0 ? `+${winRateDelta}%` : `${winRateDelta}%`})
                </span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                نیاز سر‌به‌سر: {report.binary.breakevenWinRateRequired}%
              </span>
            </div>

            {/* Total Trades & Filtered */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">معاملات / کندل‌ها:</span>
              <div className="text-2xl font-black text-slate-100 font-mono mt-1">
                {report.basic.totalTradesExecuted}{' '}
                <span className="text-sm font-normal text-slate-500">/ {report.basic.totalBarsEvaluated}</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                رد شده (NO TRADE): {report.basic.noTradeCount}
              </span>
            </div>

            {/* Total Profit */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">سود کل (${stakeAmount} استیک):</span>
              <div className={`text-2xl font-black font-mono mt-1 ${isProfitable ? 'text-emerald-400' : 'text-rose-400'}`}>
                {report.trades.length > 0 ? (
                  isProfitable ? (
                    `+$${report.trades[report.trades.length - 1].cumulativeProfitUsd}`
                  ) : (
                    `-$${Math.abs(report.trades[report.trades.length - 1].cumulativeProfitUsd)}`
                  )
                ) : (
                  '$0'
                )}
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                EV هر ترید: ${report.stats.expectedValueUsd}
              </span>
            </div>

            {/* Wilson 95% CI */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">بازه اطمینان ۹۵٪ ویلسون:</span>
              <div className="text-lg font-black text-cyan-400 font-mono mt-1">
                [{report.stats.wilsonLowerBound95}% – {report.stats.wilsonUpperBound95}%]
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                کف برد با اطمینان ۹۵٪
              </span>
            </div>

            {/* Max Drawdown */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">حداکثر افت سرمایه (DD):</span>
              <div className="text-2xl font-black text-rose-400 font-mono mt-1">
                ${report.risk.maxDrawdownUsd}
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                بیشترین باخت متوالی: {report.risk.maxConsecutiveLosses}
              </span>
            </div>

            {/* Profit Factor */}
            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 block font-mono">فاکتور سود (Profit Factor):</span>
              <div className="text-2xl font-black text-slate-100 font-mono mt-1">
                {report.risk.profitFactor}
              </div>
              <span className="text-[10px] text-slate-500 font-mono block mt-1">
                برد: {report.basic.winCount} | باخت: {report.basic.lossCount}
              </span>
            </div>
          </div>

          {/* Equity Curve SVG Chart */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                منحنی رشد تجمعی سرمایه (Cumulative Realized Equity Curve)
              </h3>
              <span className="text-xs text-slate-400 font-mono">استیک ثابت ${stakeAmount} به ازای هر سیگنال ۵ دقیقه</span>
            </div>

            <div className="h-56 w-full mt-4 flex items-center justify-center relative bg-slate-950/60 rounded-lg p-2 border border-slate-800/80">
              {report.trades.length > 0 ? (
                <svg className="w-full h-full overflow-visible" viewBox="0 0 600 150">
                  {/* Zero line */}
                  <line x1="0" y1="75" x2="600" y2="75" stroke="#334155" strokeDasharray="3 3" />

                  {(() => {
                    const maxVal = Math.max(
                      ...report.trades.map((t) => Math.abs(t.cumulativeProfitUsd)),
                      300
                    );
                    const points = report.trades
                      .map((t, idx) => {
                        const x = (idx / Math.max(1, report.trades.length - 1)) * 560 + 20;
                        const y = 75 - (t.cumulativeProfitUsd / maxVal) * 60;
                        return `${x},${y}`;
                      })
                      .join(' ');

                    return (
                      <>
                        <polyline
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="3"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={points}
                        />
                        {report.trades.map((t, idx) => {
                          const x = (idx / Math.max(1, report.trades.length - 1)) * 560 + 20;
                          const y = 75 - (t.cumulativeProfitUsd / maxVal) * 60;
                          return (
                            <circle
                              key={t.id}
                              cx={x}
                              cy={y}
                              r="3.5"
                              className={t.result === 'WIN' ? 'fill-emerald-400' : 'fill-rose-400'}
                            />
                          );
                        })}
                      </>
                    );
                  })()}
                </svg>
              ) : (
                <div className="text-xs text-slate-500 font-mono">داده کافی برای ترسیم منحنی بک‌تست وجود ندارد</div>
              )}
            </div>
          </div>

          {/* Payout Sensitivity Matrix */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
            <h3 className="text-base font-bold text-slate-100 mb-3 flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              ماتریس حساسیت سودآوری به نرخ پرداخت کارگزار (Payout Sensitivity Matrix)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono text-xs">
              {report.binary.payoutSensitivityTable.map((ps) => (
                <div
                  key={ps.payout}
                  className={`p-3 rounded-lg border ${
                    ps.payout === brokerPayout
                      ? 'bg-cyan-500/10 border-cyan-500/40'
                      : 'bg-slate-950 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between text-slate-400">
                    <span>پی‌اوت:</span>
                    <span className="font-bold text-slate-200">{ps.payout}%</span>
                  </div>
                  <div className="mt-2 text-slate-400">
                    <span>نیاز سر‌به‌سر:</span>
                    <span className="font-bold text-amber-400 mr-1">{ps.breakeven}%</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between">
                    <span className="text-slate-400">سود خالص:</span>
                    <span
                      className={`font-bold ${
                        ps.netProfitUsd >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      ${ps.netProfitUsd}
                    </span>
                  </div>
                  <div className="mt-1 text-[10px] text-slate-500">
                    EV ترید: {ps.evPercent}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 2: SETUP ANALYTICS --- */}
      {activeTab === 'setups' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {setupSummaries.map((s) => (
              <button
                key={s.setupType}
                onClick={() => setSelectedSetup(s.setupType)}
                className={`p-4 rounded-xl border text-right transition-all font-mono text-xs ${
                  selectedSetup === s.setupType
                    ? 'bg-cyan-500/15 border-cyan-500 text-slate-100 shadow-md'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-850'
                }`}
              >
                <span className="text-[10px] font-bold text-cyan-400 block truncate">{s.nameFa}</span>
                <div className="flex items-baseline justify-between mt-2">
                  <span className="text-2xl font-black text-slate-100">{s.winRate}%</span>
                  <span className="text-xs text-slate-500">{s.sampleSize} معامله</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                  <span>بازه اطمینان:</span>
                  <span className="text-slate-300">[{s.wilsonLowerBound}% - {s.wilsonUpperBound}%]</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">امید ریاضی (EV):</span>
                  <span className={s.expectancyPercent >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                    +{s.expectancyPercent}%
                  </span>
                </div>
              </button>
            ))}
          </div>

          {/* Selected Setup Detailed Deep-Dive */}
          {(() => {
            const current = setupSummaries.find((s) => s.setupType === selectedSetup) || setupSummaries[0];
            return (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-5">
                <div className="border-b border-slate-800 pb-3">
                  <span className="text-xs font-mono text-cyan-400 font-bold">{current.setupType}</span>
                  <h3 className="text-lg font-bold text-slate-100 mt-1">{current.nameFa}</h3>
                </div>

                {/* Sub-matrices for Sessions & Market Regimes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Session Matrix */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs">
                    <h4 className="font-bold text-slate-200 mb-3 flex items-center gap-1.5">
                      <Activity className="w-3.5 h-3.5 text-amber-400" />
                      عملکرد بر اساس سشن‌های معاملاتی (Session Heatmap)
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(current.sessionPerformance).map(([sess, dataVal]) => {
                        const data = dataVal as { trades: number; winRate: number };
                        return (
                          <div key={sess} className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800/80">
                            <span className="text-slate-300">{sess}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-slate-500">{data.trades} ترید</span>
                              <span
                                className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                                  data.winRate >= 65
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : data.winRate >= 55
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : 'bg-rose-500/20 text-rose-400'
                                }`}
                              >
                                {data.winRate}% Win
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Market Regime Matrix */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs">
                    <h4 className="font-bold text-slate-200 mb-3 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      عملکرد بر اساس رژیم ساختار بازار (Regime Heatmap)
                    </h4>
                    <div className="space-y-2">
                      {Object.entries(current.regimePerformance).slice(0, 5).map(([reg, dataVal]) => {
                        const data = dataVal as { trades: number; winRate: number };
                        return (
                          <div key={reg} className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800/80">
                            <span className="text-slate-300">{reg}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-slate-500">{data.trades} ترید</span>
                              <span
                                className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                                  data.winRate >= 65
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : data.winRate >= 55
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : 'bg-rose-500/20 text-rose-400'
                                }`}
                              >
                                {data.winRate}% Win
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Best & Worst Conditions */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                  <div className="bg-emerald-950/20 border border-emerald-500/30 p-4 rounded-xl">
                    <h4 className="font-bold text-emerald-400 mb-2 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" />
                      بهترین شرایط اجرای ستاپ (Optimal Conditions)
                    </h4>
                    <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
                      {current.bestConditions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="bg-rose-950/20 border border-rose-500/30 p-4 rounded-xl">
                    <h4 className="font-bold text-rose-400 mb-2 flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" />
                      بدترین شرایط و هشدارهای ابطال (Hostile Conditions)
                    </h4>
                    <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
                      {current.worstConditions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}

      {/* --- TAB 3: WALK-FORWARD VALIDATION --- */}
      {activeTab === 'walk_forward' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Compass className="w-4 h-4 text-cyan-400" />
                  اعتبارسنجی لغزان غلتان (Walk-Forward Rolling Folds)
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  سنجش تعمیم‌پذیری و مقاومت در برابر بیش‌برازش (Overfitting Prevention)
                </p>
              </div>

              <div className="flex items-center gap-3">
                <div className="bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
                  <span className="text-slate-400">شاخص بیش‌برازش:</span>
                  <span className="text-emerald-400 font-bold mr-1">{walkForwardReport.overfittingIndex}/100</span>
                </div>
                <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-lg text-xs font-bold">
                  {walkForwardReport.robustnessVerdict}
                </div>
              </div>
            </div>

            {/* Folds Table */}
            <div className="mt-4 border border-slate-800 rounded-lg overflow-x-auto bg-slate-950 text-xs">
              <table className="w-full text-right">
                <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-3">فولد (Fold)</th>
                    <th className="p-3">بازه آموزش (In-Sample)</th>
                    <th className="p-3">وین‌ریت درون‌نمونه</th>
                    <th className="p-3">بازه آزمون برون‌نمونه (OOS)</th>
                    <th className="p-3">وین‌ریت برون‌نمونه (OOS)</th>
                    <th className="p-3">افت عملکرد (Degradation)</th>
                    <th className="p-3">پایداری (Status)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {walkForwardReport.folds.map((fold) => (
                    <tr key={fold.foldIndex} className="hover:bg-slate-900/50">
                      <td className="p-3 font-bold text-cyan-400">Fold #{fold.foldIndex}</td>
                      <td className="p-3 text-slate-300">
                        {fold.trainRange.start} → {fold.trainRange.end} ({fold.inSampleTrades} trades)
                      </td>
                      <td className="p-3 font-bold text-slate-100">{fold.inSampleWinRate}%</td>
                      <td className="p-3 text-slate-300">
                        {fold.validationRange.start} → {fold.validationRange.end} ({fold.outOfSampleTrades} trades)
                      </td>
                      <td className="p-3 font-bold text-emerald-400">{fold.outOfSampleWinRate}%</td>
                      <td className={`p-3 font-bold ${fold.performanceDegradationPercent >= -5 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {fold.performanceDegradationPercent}%
                      </td>
                      <td className="p-3">
                        <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded text-[10px] font-bold">
                          ROBUST
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 4: MONTE CARLO SIMULATION --- */}
      {activeTab === 'monte_carlo' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Shuffle className="w-4 h-4 text-cyan-400" />
                  شبیه‌ساز مونت‌کارلو ۱۰,۰۰۰ مسیری (Monte Carlo Random Sequence Resampling)
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  سنجش عدم‌قطعیت، توزیع طولانی‌ترین باخت‌های متوالی و ریسک افت سرمایه
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleRunMonteCarlo}
                  className="flex items-center gap-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-xs transition-all shadow-md"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  اجرای مجدد شبیه‌سازی ({mcSimCount} مسیر)
                </button>
              </div>
            </div>

            {/* Monte Carlo Metric Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block">سود میانه (Median PnL):</span>
                <span className="text-2xl font-black text-emerald-400 block mt-1">
                  +${mcResult.medianFinalEquityUsd}
                </span>
                <span className="text-[10px] text-slate-500 block mt-1">احتمال سودآوری: {mcResult.profitProbabilityPercent}%</span>
              </div>

              <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block">صدک ۵٪ (VaR 95% Worst Case):</span>
                <span className="text-2xl font-black text-amber-400 block mt-1">
                  +${mcResult.percentile5thEquityUsd}
                </span>
                <span className="text-[10px] text-slate-500 block mt-1">بدترین سناریوی آماری</span>
              </div>

              <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block">بدترین دراودان (Worst DD):</span>
                <span className="text-2xl font-black text-rose-400 block mt-1">
                  -${mcResult.worstCaseDrawdownUsd}
                </span>
                <span className="text-[10px] text-slate-500 block mt-1">ریسک تباهی: {mcResult.riskOfRuinPercent}%</span>
              </div>

              <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block">میانگین باخت متوالی بیشینه:</span>
                <span className="text-2xl font-black text-slate-100 block mt-1">
                  {mcResult.averageMaxLosingStreak}
                </span>
                <span className="text-[10px] text-slate-500 block mt-1">تعداد باخت پشت‌سرهم</span>
              </div>
            </div>

            {/* Path Chart Preview */}
            <div className="h-44 w-full mt-4 bg-slate-950 rounded-lg border border-slate-800 p-2 relative flex items-center justify-center">
              <svg className="w-full h-full overflow-visible" viewBox="0 0 600 120">
                <line x1="0" y1="60" x2="600" y2="60" stroke="#334155" strokeDasharray="3 3" />
                {mcResult.paths.slice(0, 30).map((path, idx) => {
                  const endY = 60 - (path.finalEquityUsd / 2000) * 45;
                  return (
                    <line
                      key={idx}
                      x1="20"
                      y1="60"
                      x2="580"
                      y2={Math.max(10, Math.min(110, endY))}
                      stroke={path.finalEquityUsd >= 0 ? '#10b981' : '#f43f5e'}
                      strokeWidth="1.2"
                      strokeOpacity="0.4"
                    />
                  );
                })}
              </svg>
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 5: PARAMETER STABILITY --- */}
      {activeTab === 'parameter_stability' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 pb-3 border-b border-slate-800">
              <Sliders className="w-4 h-4 text-cyan-400" />
              تحلیل پایداری پارامترها و جلوگیری از بهینه‌سازی افراطی (Curve-Fitting Protection)
            </h3>

            <div className="space-y-6 mt-4">
              {parameterAnalyses.map((param) => (
                <div key={param.parameterName} className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                    <div>
                      <span className="text-xs text-cyan-400 font-bold">{param.parameterName}</span>
                      <h4 className="text-sm font-bold text-slate-200 mt-0.5">{param.descriptionFa}</h4>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-slate-400">بازه پایدار (Stable Plateau):</span>
                      <span className="bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded font-bold">
                        {param.stableRange.min} – {param.stableRange.max}
                      </span>
                    </div>
                  </div>

                  {/* Points Matrix */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 mt-3 text-xs">
                    {param.testPoints.map((pt) => (
                      <div
                        key={pt.parameterValue}
                        className={`p-2.5 rounded border text-center ${
                          pt.parameterValue === param.currentValue
                            ? 'bg-cyan-500/20 border-cyan-500'
                            : 'bg-slate-900 border-slate-800'
                        }`}
                      >
                        <span className="text-slate-400 block text-[10px]">مقدار: {pt.parameterValue}</span>
                        <span className="text-sm font-bold text-slate-100 block mt-1">{pt.winRate}%</span>
                        <span className="text-[10px] text-emerald-400 block">+${pt.profitUsd}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 6: FAILURE ANALYSIS --- */}
      {activeTab === 'failures' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 pb-3 border-b border-slate-800">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              سیستم عیب‌یابی و تحلیل علت ریشه‌ای سیگنال‌های ناموفق (Root Cause EDA)
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 text-xs">
              {failureRecords.slice(0, 6).map((f) => (
                <div key={f.tradeId} className="bg-slate-950 border border-slate-800 p-4 rounded-xl space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-900 pb-2">
                    <span className="text-slate-400 font-bold">{f.timeStr}</span>
                    <span className="bg-rose-500/20 text-rose-400 px-2 py-0.5 rounded font-bold text-[10px]">
                      {f.primaryRootCause}
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-500 text-[10px] block">علت اصلی شکست:</span>
                    <p className="text-slate-200 mt-0.5">{f.rootCauseDescriptionFa}</p>
                  </div>

                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800/80">
                    <span className="text-cyan-400 font-bold text-[10px] block">پیشنهاد اصلاحی الگوریتم:</span>
                    <p className="text-slate-300 mt-0.5">{f.mitigationRuleSuggestion}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 7: LIVE PAPER TRADING --- */}
      {activeTab === 'paper_trading' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  ترمینال شبیه‌ساز معاملات زنده مجازی (Real-Time Paper Trading Terminal)
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  اجرای بلادرنگ بدون ریسک سرمایه با پایپ‌لاین یکپارچه پروداکشن
                </p>
              </div>

              {/* Virtual Balance */}
              <div className="flex items-center gap-3 bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                <span className="text-slate-400">موجودی مجازی:</span>
                <span className="text-lg font-black text-emerald-400">${paperState.virtualBalanceUsd.toFixed(1)}</span>
              </div>
            </div>

            {/* Quick Virtual Execution Buttons */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                onClick={() =>
                  paperEngine.placeVirtualOrder(
                    'SETUP_A_SWEEP_ABSORPTION_REVERSAL',
                    'CALL',
                    bars[bars.length - 1]?.close || 2650,
                    100,
                    brokerPayout
                  )
                }
                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-black px-4 py-2 rounded-lg text-xs transition-all shadow-md"
              >
                <ArrowUpRight className="w-4 h-4" />
                ثبت سفارش مجازی CALL ($100 - 5M)
              </button>

              <button
                onClick={() =>
                  paperEngine.placeVirtualOrder(
                    'SETUP_A_SWEEP_ABSORPTION_REVERSAL',
                    'PUT',
                    bars[bars.length - 1]?.close || 2650,
                    100,
                    brokerPayout
                  )
                }
                className="flex items-center gap-2 bg-rose-600 hover:bg-rose-500 text-slate-950 font-black px-4 py-2 rounded-lg text-xs transition-all shadow-md"
              >
                <ArrowDownRight className="w-4 h-4" />
                ثبت سفارش مجازی PUT ($100 - 5M)
              </button>
            </div>

            {/* Active Contracts Countdown */}
            <div className="mt-5">
              <h4 className="text-xs font-bold text-slate-300 mb-2 flex items-center gap-1.5">
                <Timer className="w-3.5 h-3.5 text-amber-400" />
                قراردادهای باز فعال (Active Contracts - {paperState.activeContracts.length})
              </h4>
              {paperState.activeContracts.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                  {paperState.activeContracts.map((c) => (
                    <div key={c.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                      <div className="flex items-center justify-between">
                        <span
                          className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                            c.direction === 'CALL'
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-rose-500/20 text-rose-400'
                          }`}
                        >
                          {c.direction}
                        </span>
                        <span className="text-amber-400 font-bold">{c.secondsRemaining} ثانیه مانده</span>
                      </div>
                      <div className="mt-2 text-slate-300 text-[11px]">
                        ورود: ${c.entryPrice.toFixed(2)} | قیمت فعلی: ${c.currentPrice.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500 p-3 bg-slate-950 rounded-lg border border-slate-800 text-center">
                  هیچ قرارداد مجازی بازی در حال حاضر وجود ندارد.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- TAB 8: RESEARCH JOURNAL --- */}
      {activeTab === 'journal' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl font-mono">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2 pb-3 border-b border-slate-800">
              <BookOpen className="w-4 h-4 text-cyan-400" />
              دفترچه ثبت پژوهش کمّی و رکوردهای بردار ویژگی ML (Research Journal)
            </h3>

            <div className="mt-4 border border-slate-800 rounded-lg overflow-x-auto bg-slate-950 text-xs">
              <table className="w-full text-right">
                <thead className="bg-slate-900 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-3">زمان</th>
                    <th className="p-3">ستاپ</th>
                    <th className="p-3">جهت</th>
                    <th className="p-3">امتیاز کیفی</th>
                    <th className="p-3">نتیجه</th>
                    <th className="p-3">توضیح سیستم</th>
                    <th className="p-3">نسخه مدل</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-900">
                  {researchJournal.map((rec) => (
                    <tr key={rec.id} className="hover:bg-slate-900/50">
                      <td className="p-3 text-slate-300">{rec.timeStr}</td>
                      <td className="p-3 text-cyan-400 font-bold max-w-xs truncate">{rec.setupType}</td>
                      <td className="p-3 font-bold text-slate-100">{rec.decision}</td>
                      <td className="p-3 text-amber-400 font-bold">{rec.confidenceScore}/100</td>
                      <td className="p-3">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            rec.tradeOutcome === 'WIN'
                              ? 'bg-emerald-500 text-slate-950'
                              : 'bg-rose-500 text-slate-950'
                          }`}
                        >
                          {rec.tradeOutcome}
                        </span>
                      </td>
                      <td className="p-3 text-slate-400 max-w-xs truncate">{rec.decisionExplanation}</td>
                      <td className="p-3 text-slate-500 text-[10px]">{rec.modelVersion}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
