import React, { useState, useEffect, useMemo } from 'react';
import { Header } from './components/Header';
import { LiveArbiterCard } from './components/LiveArbiterCard';
import { FootprintViewer } from './components/FootprintViewer';
import { MarketStructurePanel } from './components/MarketStructurePanel';
import { NewsQuarantinePanel } from './components/NewsQuarantinePanel';
import { BacktestLab } from './components/BacktestLab';
import { ArchitectureView } from './components/ArchitectureView';
import { PipelineInspectorView } from './components/PipelineInspectorView';
import { IntelligenceInspectorView } from './components/IntelligenceInspectorView';
import { MarketContextInspectorView } from './components/MarketContextInspectorView';
import { DecisionEngineInspectorView } from './components/DecisionEngineInspectorView';
import { PythonExportModal } from './components/PythonExportModal';
import { DataInspectorModal } from './components/DataInspectorModal';
import { SystemHealth } from './components/SystemHealth';
import { Journal } from './components/Journal';
import { Analytics } from './components/Analytics';
import { createHistoricalFootprintBars, generateLiveTickStream, mockMarketStructure15M, mockMarketStructure1H } from './data/mockMarketData';
import { mockNewsCalendar } from './data/macroEvents';
import { FootprintBar, NormalizedTick, StrategyConfig } from './types';
import { evaluateSignal } from './utils/orderFlowEngine';
import { DataQualityEngine, FootprintEngine } from './services/dataPipelineService';
import { DataQualityReport, TickEntity } from './types/dataPipeline';

const initialConfig: StrategyConfig = {
  imbalanceRatio: 3.0,
  minStackedImbalance: 2,
  minDeltaThreshold: 150,
  absorptionVolumeThreshold: 250,
  minPayoutRequired: 0.80, // 80%
  newsQuarantineBeforeMin: 15,
  newsQuarantineAfterMin: 20,
  maxAllowedBasisSpread: 1.50,
};

export default function App() {
  const [activeTab, setActiveTab] = useState<'terminal' | 'journal' | 'analytics' | 'pipeline' | 'intelligence' | 'context' | 'decision' | 'backtest' | 'architecture'>('terminal');
  const [isLiveStream, setIsLiveStream] = useState<boolean>(true);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(142);
  const [bars, setBars] = useState<FootprintBar[]>(() => createHistoricalFootprintBars());
  const [selectedBarId, setSelectedBarId] = useState<string>(() => bars[bars.length - 1]?.id || 'bar-8');
  
  const [gcPrice, setGcPrice] = useState<number>(2646.5);
  const [spotPrice, setSpotPrice] = useState<number>(2646.1);
  const [payoutRate, setPayoutRate] = useState<number>(0.85);

  const [recentTicks, setRecentTicks] = useState<NormalizedTick[]>([]);
  const [isPythonModalOpen, setIsPythonModalOpen] = useState<boolean>(false);
  const [isDataModalOpen, setIsDataModalOpen] = useState<boolean>(false);

  // Phase 1: Data Pipeline Engine Instances
  const qualityEngine = useMemo(() => new DataQualityEngine(), []);
  const footprintEngine = useMemo(() => new FootprintEngine(), []);

  const [tickCounter, setTickCounter] = useState<number>(14852);
  const [qualityReport, setQualityReport] = useState<DataQualityReport>({
    timestamp: Date.now(),
    score: 100,
    state: 'GOOD',
    missingTicksDetected: 0,
    duplicateTicksDropped: 0,
    outOfOrderFixed: 0,
    invalidVolumeCount: 0,
    invalidPriceCount: 0,
    feedDelayMs: 3.2,
    syncOffsetMs: 0.4,
    reasons: [],
    shouldHaltProcessing: false
  });

  // Current active bar being analyzed
  const currentBar = bars.find((b) => b.id === selectedBarId) || bars[bars.length - 1];

  // Evaluate Live Arbiter decision for current bar
  const currentDecision = evaluateSignal(
    currentBar,
    mockMarketStructure15M,
    mockMarketStructure1H,
    mockNewsCalendar,
    initialConfig,
    payoutRate,
    spotPrice,
    gcPrice
  );

  const isNewsQuarantineActive = currentDecision.newsBlockActive;

  // 5-Minute Timer Countdown & Live Tick Generator Simulation
  useEffect(() => {
    if (!isLiveStream) return;

    const interval = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          return 300;
        }
        return prev - 1;
      });

      const newTick = generateLiveTickStream(gcPrice);
      setGcPrice(newTick.price);
      const newSpot = Number((newTick.price - 0.4 + (Math.random() - 0.5) * 0.1).toFixed(1));
      setSpotPrice(newSpot);

      const tickEntity: TickEntity = {
        id: newTick.id,
        timestamp: newTick.timestamp,
        symbol: 'GC_FUT',
        price: newTick.price,
        size: newTick.size,
        bid: newTick.bidPrice,
        ask: newTick.askPrice,
        side: newTick.aggressorSide,
        source: 'CME_FEED',
        classificationMethod: 'DIRECT_FLAG'
      };

      const validation = qualityEngine.validateTick(tickEntity, newSpot);
      setQualityReport(validation.report);
      setTickCounter((prev) => prev + 1);

      if (validation.isValid) {
        footprintEngine.processTick(tickEntity);
      }

      setRecentTicks((prev) => [newTick, ...prev.slice(0, 49)]);

      setBars((prevBars) => {
        const lastIdx = prevBars.length - 1;
        const lastBar = prevBars[lastIdx];
        if (!lastBar) return prevBars;

        const updatedBar = { ...lastBar };
        updatedBar.volume += newTick.size;
        updatedBar.close = newTick.price;
        if (newTick.price > updatedBar.high) updatedBar.high = newTick.price;
        if (newTick.price < updatedBar.low) updatedBar.low = newTick.price;

        if (newTick.aggressorSide === 'BUY') {
          updatedBar.delta += newTick.size;
          updatedBar.cvd += newTick.size;
        } else if (newTick.aggressorSide === 'SELL') {
          updatedBar.delta -= newTick.size;
          updatedBar.cvd -= newTick.size;
        }

        const newBars = [...prevBars];
        newBars[lastIdx] = updatedBar;
        return newBars;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [isLiveStream, gcPrice, qualityEngine, footprintEngine]);

  const handleSimulateAnomaly = (type: 'DUPLICATE' | 'OUT_OF_ORDER' | 'INVALID_SPREAD' | 'SYNC_ANOMALY') => {
    const now = Date.now();
    let mockTick: TickEntity;

    if (type === 'DUPLICATE') {
      mockTick = {
        id: 'dup-tick-fixed-id',
        timestamp: now,
        symbol: 'GC_FUT',
        price: gcPrice,
        size: 10,
        bid: gcPrice - 0.1,
        ask: gcPrice + 0.1,
        side: 'BUY',
        source: 'CME_FEED',
        classificationMethod: 'DIRECT_FLAG'
      };
      qualityEngine.validateTick(mockTick);
      const res = qualityEngine.validateTick(mockTick);
      setQualityReport(res.report);
    } else if (type === 'OUT_OF_ORDER') {
      mockTick = {
        id: `ooo-${now}`,
        timestamp: now - 5000,
        symbol: 'GC_FUT',
        price: gcPrice,
        size: 15,
        bid: gcPrice - 0.1,
        ask: gcPrice + 0.1,
        side: 'SELL',
        source: 'CME_FEED',
        classificationMethod: 'DIRECT_FLAG'
      };
      const res = qualityEngine.validateTick(mockTick);
      setQualityReport(res.report);
    } else if (type === 'INVALID_SPREAD') {
      mockTick = {
        id: `inv-spread-${now}`,
        timestamp: now,
        symbol: 'GC_FUT',
        price: gcPrice,
        size: 20,
        bid: 2650.0,
        ask: 2640.0,
        side: 'SELL',
        source: 'CME_FEED',
        classificationMethod: 'DIRECT_FLAG'
      };
      const res = qualityEngine.validateTick(mockTick);
      setQualityReport(res.report);
    } else {
      mockTick = {
        id: `sync-bad-${now}`,
        timestamp: now,
        symbol: 'GC_FUT',
        price: gcPrice + 12.0,
        size: 10,
        bid: gcPrice + 11.9,
        ask: gcPrice + 12.1,
        side: 'BUY',
        source: 'CME_FEED',
        classificationMethod: 'DIRECT_FLAG'
      };
      const res = qualityEngine.validateTick(mockTick, spotPrice);
      setQualityReport(res.report);
    }
  };

  const handleResetQuality = () => {
    qualityEngine.reset();
    setQualityReport({
      timestamp: Date.now(),
      score: 100,
      state: 'GOOD',
      missingTicksDetected: 0,
      duplicateTicksDropped: 0,
      outOfOrderFixed: 0,
      invalidVolumeCount: 0,
      invalidPriceCount: 0,
      feedDelayMs: 2.1,
      syncOffsetMs: 0.4,
      reasons: [],
      shouldHaltProcessing: false
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-amber-500/30 selection:text-amber-200">
      
      {/* Top Fixed Header */}
      <Header
        isLiveStream={isLiveStream}
        onToggleLiveStream={() => setIsLiveStream(!isLiveStream)}
        secondsRemaining={secondsRemaining}
        gcPrice={gcPrice}
        spotPrice={spotPrice}
        onOpenPythonModal={() => setIsPythonModalOpen(true)}
        onOpenDataModal={() => setIsDataModalOpen(true)}
        activeTab={activeTab as any}
        setActiveTab={setActiveTab as any}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        
        {/* Real-Time Telemetry Watchdog */}
        <SystemHealth
          latencyMs={qualityReport.feedDelayMs}
          provider="NINJATRADER 8 BRIDGE"
          connectionState={isLiveStream ? 'CONNECTED' : 'DISCONNECTED'}
          qualityScore={qualityReport.score}
          processedTicksCount={tickCounter}
          lastMessageTime={new Date().toLocaleTimeString()}
        />

        {activeTab === 'terminal' && (
          <>
            {/* Decision Arbiter Master Card */}
            <LiveArbiterCard
              decision={currentDecision}
              currentPayout={payoutRate}
              onChangePayout={(payout) => setPayoutRate(payout)}
            />

            {/* Footprint Matrix & Price Ladder */}
            <FootprintViewer
              bars={bars}
              selectedBarId={selectedBarId}
              onSelectBar={(id) => setSelectedBarId(id)}
            />

            {/* Context: HTF Structure & Macro News Quarantine */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <MarketStructurePanel
                structure15M={mockMarketStructure15M}
                structure1H={mockMarketStructure1H}
                currentPrice={gcPrice}
              />

              <NewsQuarantinePanel
                newsEvents={mockNewsCalendar}
                isQuarantineActive={isNewsQuarantineActive}
              />
            </div>
          </>
        )}

        {activeTab === 'journal' && <Journal />}

        {activeTab === 'analytics' && <Analytics />}

        {activeTab === 'pipeline' && (
          <PipelineInspectorView
            currentQualityReport={qualityReport}
            deltaState={footprintEngine.getDeltaEngineState()}
            processedTickCount={tickCounter}
            onSimulateTickAnomaly={handleSimulateAnomaly}
            onResetQuality={handleResetQuality}
          />
        )}

        {activeTab === 'intelligence' && (
          <IntelligenceInspectorView
            currentBar={bars.find(b => b.id === selectedBarId) || bars[bars.length - 1]}
            historicalBars={bars}
          />
        )}

        {activeTab === 'context' && (
          <MarketContextInspectorView
            bars={bars}
            dataQualityScore={qualityReport.score}
          />
        )}

        {activeTab === 'decision' && (
          <DecisionEngineInspectorView
            currentBar={bars.find(b => b.id === selectedBarId) || bars[bars.length - 1]}
            historicalBars={bars}
            dataQualityScore={qualityReport.score}
          />
        )}

        {activeTab === 'backtest' && (
          <BacktestLab
            bars={bars}
            structure15M={mockMarketStructure15M}
            structure1H={mockMarketStructure1H}
            newsEvents={mockNewsCalendar}
            config={initialConfig}
          />
        )}

        {activeTab === 'architecture' && <ArchitectureView />}

      </main>

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-900 py-4 px-6 text-center text-xs text-slate-500 font-mono">
        FO-X 5M Research Engine &bull; Futures Order Flow XAU/USD 5-Minute Quantitative System &bull; خروجی اکیداً سه‌حالته [ CALL | PUT | NO TRADE ]
      </footer>

      {/* Python Code Export Modal */}
      <PythonExportModal
        isOpen={isPythonModalOpen}
        onClose={() => setIsPythonModalOpen(false)}
      />

      {/* Raw Data & L2 Tick Inspector Modal */}
      <DataInspectorModal
        isOpen={isDataModalOpen}
        onClose={() => setIsDataModalOpen(false)}
        recentTicks={recentTicks}
      />

    </div>
  );
}
