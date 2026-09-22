import { FootprintBar, NormalizedTick, PriceLevelVolume } from '../types';

export type TradeSide = 'BUY' | 'SELL' | 'UNKNOWN';
export type QualityState = 'GOOD' | 'DEGRADED' | 'INVALID';

export interface TickEntity {
  id: string;
  timestamp: number; // UTC microsecond/millisecond
  symbol: 'GC_FUT' | 'XAUUSD_SPOT';
  price: number;
  size: number;
  bid: number;
  ask: number;
  side: TradeSide;
  source: 'CME_FEED' | 'SPOT_FEED' | 'SYNTHETIC_REPLAY';
  classificationMethod: 'DIRECT_FLAG' | 'LEE_READY' | 'UNKNOWN_NEUTRAL';
}

export interface DataQualityReport {
  timestamp: number;
  score: number; // 0 - 100
  state: QualityState;
  missingTicksDetected: number;
  duplicateTicksDropped: number;
  outOfOrderFixed: number;
  invalidVolumeCount: number;
  invalidPriceCount: number;
  feedDelayMs: number;
  syncOffsetMs: number;
  reasons: string[];
  shouldHaltProcessing: boolean;
}

export interface DeltaEngineState {
  candleDelta: number;
  rollingDelta5m: number;
  sessionDelta: number;
  swingDelta: number;
  sessionCvd: number;
  rollingCvd5m: number;
  swingCvd: number;
  lastResetTimestamp: number;
}

export interface HistoricalReplayConfig {
  speedMultiplier: number; // 1x, 5x, 10x, max
  startEpochMs: number;
  endEpochMs: number;
  chunkSize: number;
  preserveRealTimeSemantics: boolean; // Prevent lookahead bias
}
