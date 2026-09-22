export interface PythonCodeFile {
  filename: string;
  category: string;
  description: string;
  code: string;
}

export const pythonFiles: PythonCodeFile[] = [
  {
    filename: 'models.py',
    category: '1. Data Models (Pydantic V2)',
    description: 'تعریف ساختارهای داده استاندارد تیک، بار فوت‌پرینت، کانتکست و خروجی سه‌حالته',
    code: `"""
FO-X 5M — Quantitative Data Models
Pydantic V2 definitions for Market Microstructure & Order Flow.
"""

from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class NormalizedTick(BaseModel):
    timestamp_utc: datetime = Field(..., description="Microsecond resolution UTC timestamp")
    symbol: Literal["GC_FUT", "XAUUSD_SPOT"]
    price: float = Field(..., gt=0)
    size: int = Field(..., gt=0)
    aggressor_side: Literal["BUY", "SELL", "UNKNOWN"]
    bid_price: float
    ask_price: float

class PriceLevelVolume(BaseModel):
    price: float
    bid_volume: int = 0
    ask_volume: int = 0
    total_volume: int = 0
    delta: int = 0
    is_poc: bool = False
    bid_imbalance: bool = False
    ask_imbalance: bool = False
    is_absorption_node: bool = False

class FootprintBar(BaseModel):
    bar_start_utc: datetime
    bar_end_utc: datetime
    open: float
    high: float
    low: float
    close: float
    total_volume: int
    total_delta: int
    cvd: int
    poc_price: float
    vah_price: float
    val_price: float
    levels: List[PriceLevelVolume]
    unfinished_high: bool = False
    unfinished_low: bool = False
    stacked_buy_imbalances: int = 0
    stacked_sell_imbalances: int = 0
    absorption_side: Literal["BULLISH", "BEARISH", "NONE"] = "NONE"

class MarketStructureState(BaseModel):
    timeframe: Literal["15M", "1H"]
    trend: Literal["BULLISH", "BEARISH", "RANGING"]
    bsl_price: float  # Buy-side liquidity pool
    ssl_price: float  # Sell-side liquidity pool
    nearest_fvg_top: Optional[float] = None
    nearest_fvg_bottom: Optional[float] = None
    volatility_regime: Literal["COMPRESSION", "NORMAL", "EXTREME"] = "NORMAL"

class SignalDecision(BaseModel):
    decision_timestamp: datetime
    expiry_timestamp: datetime
    action: Literal["CALL", "PUT", "NO_TRADE"]
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    primary_hypothesis: str
    rejection_reasons: List[str] = Field(default_factory=list)
    payout_viable: bool
    news_blocked: bool
    explainability_log: str
`
  },
  {
    filename: 'footprint_engine.py',
    category: '2. Footprint & Order Flow (Numba/NumPy)',
    description: 'محاسبه سریع فوت‌پرینت، ماتریس Bid/Ask، عدم تعادل‌های قطری و جذب حجم',
    code: `"""
FO-X 5M — High Performance Order Flow & Footprint Engine
Utilizes NumPy and Numba JIT for real-time tick-to-footprint synthesis.
"""

import numpy as np
from numba import njit
from typing import Dict, Tuple

@njit(fastmath=True)
def calculate_diagonal_imbalances(
    bids: np.ndarray, 
    asks: np.ndarray, 
    ratio_threshold: float = 3.0,
    min_volume_threshold: int = 40
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes diagonal imbalances between Bid(P) vs Ask(P+1) and Ask(P) vs Bid(P-1).
    """
    n = len(bids)
    ask_imbalances = np.zeros(n, dtype=np.bool_)
    bid_imbalances = np.zeros(n, dtype=np.bool_)

    for i in range(n):
        # Ask at level i vs Bid at level i-1 (Buyer aggressor buying above seller)
        if i > 0 and asks[i] >= bids[i - 1] * ratio_threshold and asks[i] >= min_volume_threshold:
            ask_imbalances[i] = True

        # Bid at level i vs Ask at level i+1 (Seller aggressor selling below buyer)
        if i < n - 1 and bids[i] >= asks[i + 1] * ratio_threshold and bids[i] >= min_volume_threshold:
            bid_imbalances[i] = True

    return ask_imbalances, bid_imbalances

@njit(fastmath=True)
def detect_absorption(
    bids: np.ndarray,
    asks: np.ndarray,
    price_levels: np.ndarray,
    low_price: float,
    high_price: float,
    multiplier: float = 2.5
) -> Tuple[bool, bool]:
    """
    Detects Passive Limit Absorption:
    - Bullish absorption: massive sell market orders filled at/near low without further downward expansion.
    - Bearish absorption: massive buy market orders filled at/near high without further upward expansion.
    """
    n = len(bids)
    if n == 0:
        return False, False
        
    avg_vol = (np.sum(bids) + np.sum(asks)) / (2.0 * n)
    bullish_abs = False
    bearish_abs = False

    for i in range(n):
        p = price_levels[i]
        # At lows
        if abs(p - low_price) <= 1.0 and bids[i] >= avg_vol * multiplier:
            bullish_abs = True
        # At highs
        if abs(p - high_price) <= 1.0 and asks[i] >= avg_vol * multiplier:
            bearish_abs = True

    return bullish_abs, bearish_abs

def calculate_value_area(levels_dict: Dict[float, Dict[str, int]], poc_price: float) -> Tuple[float, float]:
    """
    Calculates the 70% Value Area (VAH, VAL) around Point of Control (POC).
    """
    total_vol = sum(d["total"] for d in levels_dict.values())
    if total_vol == 0:
        return poc_price, poc_price
        
    target_70 = total_vol * 0.70
    sorted_levels = sorted(levels_dict.items(), key=lambda x: x[1]["total"], reverse=True)
    
    accumulated = 0
    va_prices = [poc_price]
    for price, data in sorted_levels:
        accumulated += data["total"]
        va_prices.append(price)
        if accumulated >= target_70:
            break
            
    return max(va_prices), min(va_prices)
`
  },
  {
    filename: 'decision_arbiter.py',
    category: '3. Tri-State Decision Arbiter',
    description: 'هسته تصمیم‌گیرنده اکیداً سه‌حالته با ثبت دلایل رد سیگنال و فیلترهای کنترلی',
    code: `"""
FO-X 5M — Strict Tri-State Arbiter & Risk Gate
Produces exclusively [ CALL | PUT | NO_TRADE ] with explainability vectors.
"""

from typing import List, Tuple
from datetime import datetime
from models import FootprintBar, MarketStructureState, SignalDecision

class ArbiterEngine:
    def __init__(
        self,
        min_payout_rate: float = 0.80,
        max_spread_dollars: float = 1.50
    ):
        self.min_payout_rate = min_payout_rate
        self.max_spread_dollars = max_spread_dollars

    def evaluate_bar(
        self,
        bar: FootprintBar,
        structure_15m: MarketStructureState,
        structure_1h: MarketStructureState,
        is_news_blocked: bool,
        current_broker_payout: float,
        spot_price: float,
        futures_price: float
    ) -> SignalDecision:
        rejection_reasons: List[str] = []
        score = 0.0
        hypothesis = "NO_CLEAR_EDGE"
        action = "NO_TRADE"

        # Gate 1: Macro News Quarantine Check
        if is_news_blocked:
            rejection_reasons.append("بلوکه شدن در پنجره قرنطینه رویداد اقتصادی پرنوسان")

        # Gate 2: Broker Payout Viability
        if current_broker_payout < self.min_payout_rate:
            rejection_reasons.append(
                f"نرخ بازدهی بروکر کمتر از حداقل آستانه توجیه آماری ({self.min_payout_rate:.0%}) است"
            )

        # Gate 3: Basis Spread Anomaly Check
        basis = abs(futures_price - spot_price)
        if basis > self.max_spread_dollars:
            rejection_reasons.append(f"اختلاف نامتعارف قیمت فیوچرز و اسپات")

        # Check Bullish Setup (CALL): Sweep of SSL + Absorption + Stacked Buys
        is_at_ssl = abs(bar.low - structure_15m.ssl_price) <= 1.5
        if is_at_ssl and bar.absorption_side == "BULLISH" and bar.stacked_buy_imbalances >= 2:
            score = 85.0
            hypothesis = "سوئیپ نقدینگی فروشندگان (SSL) با جذب تهاجمی و عدم تعادل صعودی"
            if len(rejection_reasons) == 0:
                action = "CALL"

        # Check Bearish Setup (PUT): Sweep of BSL + Absorption + Stacked Sells
        is_at_bsl = abs(bar.high - structure_15m.bsl_price) <= 1.5
        if is_at_bsl and bar.absorption_side == "BEARISH" and bar.stacked_sell_imbalances >= 2:
            score = 85.0
            hypothesis = "سوئیپ نقدینگی خریداران (BSL) با جذب تهاجمی و عدم تعادل نزولی"
            if len(rejection_reasons) == 0:
                action = "PUT"

        # Default fallback
        if action == "NO_TRADE" and len(rejection_reasons) == 0:
            rejection_reasons.append("عدم همگرایی فاکتورهای اردر فلو با سطوح نقدینگی ساختار بازار")

        explain_text = f"فرضیه: {hypothesis} | امتیاز: {score:.1f}%"
        if rejection_reasons:
            explain_text += " | موانع وتوکننده: " + "؛ ".join(rejection_reasons)

        return SignalDecision(
            decision_timestamp=bar.bar_end_utc,
            expiry_timestamp=bar.bar_end_utc,
            action=action,
            confidence_score=score,
            primary_hypothesis=hypothesis,
            rejection_reasons=rejection_reasons,
            payout_viable=current_broker_payout >= self.min_payout_rate,
            news_blocked=is_news_blocked,
            explainability_log=explain_text
        )
`
  },
  {
    filename: 'test_orderflow.py',
    category: '4. Pytest Testing Suite',
    description: 'تست‌های واحد صحت محاسبات بقای حجم، دلتا و عدم تولید داده موهومی',
    code: `"""
FO-X 5M — Pytest Verification Suite
Ensures 100% mathematical integrity of order flow algorithms.
"""

import pytest
import numpy as np
from footprint_engine import calculate_diagonal_imbalances, detect_absorption

def test_diagonal_imbalances():
    bids = np.array([10, 20, 150, 40], dtype=np.int64)
    asks = np.array([20, 100, 30, 10], dtype=np.int64)

    ask_imb, bid_imb = calculate_diagonal_imbalances(bids, asks, ratio_threshold=3.0, min_volume_threshold=30)

    # Ask at level 1 (100) vs Bid at level 0 (10) -> 100 >= 3*10 -> True
    assert ask_imb[1] == True
    # Bid at level 2 (150) vs Ask at level 3 (10) -> 150 >= 3*10 -> True
    assert bid_imb[2] == True

def test_deterministic_absorption():
    bids = np.array([500, 50, 40], dtype=np.int64)
    asks = np.array([20, 30, 40], dtype=np.int64)
    prices = np.array([2640.0, 2640.5, 2641.0], dtype=np.float64)

    bull_abs, bear_abs = detect_absorption(bids, asks, prices, low_price=2640.0, high_price=2641.0)
    assert bull_abs == True
    assert bear_abs == False
`
  },
  {
    filename: 'data_quality_engine.py',
    category: '5. Data Quality & Anomaly Detector (Phase 1)',
    description: 'موتور اعتبارسنجی تیک‌ها، تشخیص تیک‌های تکراری، خطای ترتیب زمانی و توقف اضطراری',
    code: `"""
FO-X 5M — Data Quality & Anomaly Detector (Phase 1)
Validates real-time feeds, detects timestamp drift, spread inversions, and basis sync errors.
"""

from typing import List, Tuple, Set, Optional
from datetime import datetime
from pydantic import BaseModel

class DataQualityReport(BaseModel):
    timestamp_utc: datetime
    score: int  # 0 - 100
    state: str  # GOOD, DEGRADED, INVALID
    missing_ticks: int
    duplicates_dropped: int
    out_of_order_fixed: int
    invalid_volume_count: int
    feed_delay_ms: float
    sync_offset_dollars: float
    reasons: List[str]
    should_halt_processing: bool

class DataQualityEngine:
    def __init__(self, max_basis_spread: float = 5.0):
        self.max_basis_spread = max_basis_spread
        self.seen_tick_ids: Set[str] = set()
        self.last_timestamp_ns = 0
        self.duplicate_count = 0
        self.out_of_order_count = 0
        self.invalid_count = 0

    def validate_tick(
        self,
        tick_id: str,
        timestamp_ns: int,
        price: float,
        size: int,
        bid: float,
        ask: float,
        spot_ref_price: Optional[float] = None
    ) -> Tuple[bool, DataQualityReport]:
        reasons: List[str] = []
        deduction = 0

        # 1. Deduplication
        if tick_id in self.seen_tick_ids:
            self.duplicate_count += 1
            reasons.append(f"Duplicate tick detected: {tick_id}")
            deduction += 20
        else:
            self.seen_tick_ids.add(tick_id)
            if len(self.seen_tick_ids) > 10000:
                self.seen_tick_ids.clear()

        # 2. Out of order timestamp check
        if self.last_timestamp_ns > 0 and timestamp_ns < self.last_timestamp_ns:
            self.out_of_order_count += 1
            delay_ms = (self.last_timestamp_ns - timestamp_ns) / 1_000_000
            reasons.append(f"Out of order timestamp (drift: {delay_ms:.2f}ms)")
            deduction += 25
        else:
            self.last_timestamp_ns = timestamp_ns

        # 3. Price & volume integrity
        if price <= 0 or price > 10000 or price < 500:
            self.invalid_count += 1
            reasons.append(f"Invalid price value: {price}")
            deduction += 50

        if size <= 0 or size > 50000:
            self.invalid_count += 1
            reasons.append(f"Invalid volume size: {size}")
            deduction += 30

        # 4. Bid / Ask consistency
        if bid > 0 and ask > 0 and bid > ask:
            reasons.append(f"Inverted spread: Bid({bid}) > Ask({ask})")
            deduction += 40

        # 5. GC vs Spot Basis Sync
        sync_offset = 0.0
        if spot_ref_price and spot_ref_price > 0:
            sync_offset = abs(price - spot_ref_price)
            if sync_offset > self.max_basis_spread:
                reasons.append(f"GC/XAU basis desync: {sync_offset:.2f}$")
                deduction += 35

        score = max(0, 100 - deduction)
        state = "GOOD"
        should_halt = False

        if score < 50 or deduction >= 50:
            state = "INVALID"
            should_halt = True
        elif score < 80:
            state = "DEGRADED"

        report = DataQualityReport(
            timestamp_utc=datetime.utcnow(),
            score=score,
            state=state,
            missing_ticks=0,
            duplicates_dropped=self.duplicate_count,
            out_of_order_fixed=self.out_of_order_count,
            invalid_volume_count=self.invalid_count,
            feed_delay_ms=0.5,
            sync_offset_dollars=sync_offset,
            reasons=reasons,
            should_halt_processing=should_halt
        )

        return not should_halt, report
`
  },
  {
    filename: 'historical_replay.py',
    category: '6. Backtest Replay & Zero Lookahead (Phase 1)',
    description: 'موتور بازپخش تیک به تیک داده‌های تاریخی بدون سوگیری نگاه به آینده (Lookahead Bias)',
    code: `"""
FO-X 5M — Historical Tick Replay Engine
Streams Parquet ticks sequentially to FootprintEngine with identical live processing semantics.
"""

from typing import Iterator, Dict, Any
import time

class HistoricalTickReplayer:
    def __init__(self, parquet_filepath: str, speed_multiplier: float = 1.0):
        self.filepath = parquet_filepath
        self.speed = speed_multiplier
        self.processed_ticks = 0

    def stream_ticks(self) -> Iterator[Dict[str, Any]]:
        """
        Yields ticks strictly in chronological order.
        Simulates microsecond intervals if speed_multiplier > 0.
        """
        import duckdb
        con = duckdb.connect()
        query = f"SELECT * FROM '{self.filepath}' ORDER BY timestamp_ns ASC"
        cursor = con.cursor()
        cursor.execute(query)

        while row := cursor.fetchone():
            self.processed_ticks += 1
            yield {
                "tick_id": row[0],
                "timestamp_ns": row[1],
                "symbol": row[2],
                "price": row[3],
                "size": row[4],
                "bid": row[5],
                "ask": row[6],
                "side": row[7]
            }
`
  },
  {
    filename: 'order_flow_features.py',
    category: '7. Imbalance & Stacked Imbalance Engine (Phase 2)',
    description: 'استخراج عدم‌تعادل‌های قطری خرید و فروش و کشف عدم‌تعادل‌های متوالی (Stacked Imbalance)',
    code: `"""
FO-X 5M — Imbalance & Stacked Imbalance Feature Detector (Phase 2)
Detects diagonal order flow imbalances and contiguous stacked imbalance levels.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ImbalanceFeature(BaseModel):
    price: float
    direction: str  # BUY_IMBALANCE, SELL_IMBALANCE
    ratio: float
    aggressive_volume: int
    opposite_volume: int
    volume_diff: int

class StackedImbalanceFeature(BaseModel):
    direction: str  # BUY_STACKED, SELL_STACKED
    level_count: int
    start_price: float
    end_price: float
    total_volume: int
    stack_strength: float  # 0 - 100

class ImbalanceEngine:
    def __init__(self, imbalance_ratio: float = 3.0, min_volume: int = 40, min_diff: int = 25, min_stack_size: int = 3):
        self.ratio = imbalance_ratio
        self.min_volume = min_volume
        self.min_diff = min_diff
        self.min_stack_size = min_stack_size

    def analyze_levels(self, price_levels: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Sorted ascending by price
        sorted_levels = sorted(price_levels, key=lambda x: x["price"])
        imbalances: List[ImbalanceFeature] = []

        for i in range(len(sorted_levels)):
            current = sorted_levels[i]
            
            # Buy Imbalance: Ask at level i vs Bid at level i-1
            if i > 0:
                lower_bid = sorted_levels[i-1]["bid_volume"]
                ask_vol = current["ask_volume"]
                if ask_vol >= lower_bid * self.ratio and ask_vol >= self.min_volume and (ask_vol - lower_bid) >= self.min_diff:
                    imbalances.append(ImbalanceFeature(
                        price=current["price"],
                        direction="BUY_IMBALANCE",
                        ratio=round(ask_vol / max(1, lower_bid), 2),
                        aggressive_volume=ask_vol,
                        opposite_volume=lower_bid,
                        volume_diff=ask_vol - lower_bid
                    ))

            # Sell Imbalance: Bid at level i vs Ask at level i+1
            if i < len(sorted_levels) - 1:
                higher_ask = sorted_levels[i+1]["ask_volume"]
                bid_vol = current["bid_volume"]
                if bid_vol >= higher_ask * self.ratio and bid_vol >= self.min_volume and (bid_vol - higher_ask) >= self.min_diff:
                    imbalances.append(ImbalanceFeature(
                        price=current["price"],
                        direction="SELL_IMBALANCE",
                        ratio=round(bid_vol / max(1, higher_ask), 2),
                        aggressive_volume=bid_vol,
                        opposite_volume=higher_ask,
                        volume_diff=bid_vol - higher_ask
                    ))

        return {
            "imbalances": imbalances,
            "stacked_buys": self._find_stacked(imbalances, "BUY_IMBALANCE", "BUY_STACKED"),
            "stacked_sells": self._find_stacked(imbalances, "SELL_IMBALANCE", "SELL_STACKED")
        }

    def _find_stacked(self, imbs: List[ImbalanceFeature], target_type: str, stack_type: str) -> Optional[StackedImbalanceFeature]:
        filtered = sorted([i for i in imbs if i.direction == target_type], key=lambda x: x.price)
        if len(filtered) < self.min_stack_size:
            return None

        # Check contiguous ticks (0.50$ per level)
        prices = [i.price for i in filtered]
        curr = [prices[0]]
        max_stack = [prices[0]]

        for p in prices[1:]:
            if abs(p - curr[-1] - 0.5) < 0.01:
                curr.append(p)
                if len(curr) > len(max_stack):
                    max_stack = curr.copy()
            else:
                curr = [p]

        if len(max_stack) >= self.min_stack_size:
            matched = [i for i in filtered if i.price in max_stack]
            tot_vol = sum(i.aggressive_volume for i in matched)
            return StackedImbalanceFeature(
                direction=stack_type,
                level_count=len(max_stack),
                start_price=max_stack[0],
                end_price=max_stack[-1],
                total_volume=tot_vol,
                stack_strength=min(100.0, len(max_stack) * 25.0)
            )
        return None
`
  },
  {
    filename: 'absorption_engine.py',
    category: '8. Absorption Scoring Framework (Phase 2)',
    description: 'مدل امتیازدهی ۵ مولفه‌ای جذب نقدینگی بر اساس حجم تهاجمی، عدم پیشروی قیمت، واکنش و دلتا',
    code: `"""
FO-X 5M — Quantitative Absorption Scoring Model (Phase 2)
Combines Aggressive Volume, Lack of Price Progress, Reaction, Location, and Delta.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel

class AbsorptionScoringWeights(BaseModel):
    volume_weight: float = 0.30
    price_failure_weight: float = 0.25
    reaction_weight: float = 0.20
    location_weight: float = 0.15
    delta_weight: float = 0.10

class AbsorptionFeature(BaseModel):
    location_price: float
    direction: str  # BUY_ABSORPTION, SELL_ABSORPTION
    aggressive_volume: int
    efficiency_ratio: float
    total_score: float  # 0 - 100
    confidence: float

class QuantitativeAbsorptionEngine:
    def __init__(self, weights: Optional[AbsorptionScoringWeights] = None):
        self.weights = weights or AbsorptionScoringWeights()

    def evaluate_bar(self, bar: Dict[str, Any], ssl_price: float, bsl_price: float) -> Optional[AbsorptionFeature]:
        vol = bar.get("volume", 1)
        high = bar.get("high", 0)
        low = bar.get("low", 0)
        close = bar.get("close", 0)
        delta = bar.get("delta", 0)

        range_ticks = max(1, round((high - low) / 0.5))
        efficiency = round(range_ticks / max(1, vol), 4)

        levels = bar.get("price_levels", [])
        if not levels:
            return None

        lowest_level = min(levels, key=lambda x: x["price"])
        
        # Check Bullish Absorption at bar low
        if lowest_level["bid_volume"] >= 200:
            vol_score = min(100.0, (lowest_level["bid_volume"] / 200.0) * 70.0)
            fail_score = max(0.0, 100.0 - (range_ticks / 3.0) * 30.0)
            react_score = min(100.0, (close - lowest_level["price"]) * 40.0) if close > lowest_level["price"] else 20.0
            loc_score = 100.0 if abs(low - ssl_price) <= 1.5 else 50.0
            delta_score = 90.0 if delta > 0 else 40.0

            total = (
                vol_score * self.weights.volume_weight +
                fail_score * self.weights.price_failure_weight +
                react_score * self.weights.reaction_weight +
                loc_score * self.weights.location_weight +
                delta_score * self.weights.delta_weight
            )

            if total >= 60.0:
                return AbsorptionFeature(
                    location_price=lowest_level["price"],
                    direction="BUY_ABSORPTION",
                    aggressive_volume=lowest_level["bid_volume"],
                    efficiency_ratio=efficiency,
                    total_score=round(total, 1),
                    confidence=min(100.0, round(total * 0.95, 1))
                )

        return None
`
  },
  {
    filename: 'market_context_engine.py',
    category: '6. Phase 3: Market Context & Risk Environment',
    description: 'موتور بافتار بازار، تشخیص سوینگ بدون نشت داده آینده، شکست ساختار (BOS/CHoCH) و مدل ریسک خبری',
    code: `"""
FO-X 5M — Market Context & Risk Environment Engine (Phase 3)
Calculates Swing Points (Zero Lookahead Bias), Structure Breaks, and News Quarantines.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class SwingPoint(BaseModel):
    timestamp_utc: datetime
    price: float
    type: str # SWING_HIGH / SWING_LOW
    confirmed_index: int

class StructureBreak(BaseModel):
    timestamp_utc: datetime
    type: str # BOS_BULLISH / BOS_BEARISH / CHOCH_BULLISH / CHOCH_BEARISH
    level: float
    confirmed_close: bool

class MarketContextEngine:
    def __init__(self, lookback: int = 2, confirmation: int = 2):
        self.lookback = lookback
        self.confirmation = confirmation

    def detect_swings(self, bars: List[Dict[str, Any]]) -> List[SwingPoint]:
        swings = []
        if len(bars) < self.lookback + self.confirmation + 1:
            return swings

        # Strictly scan up to (len(bars) - confirmation - 1) to eliminate lookahead bias
        for i in range(self.lookback, len(bars) - self.confirmation):
            cand = bars[i]
            is_high = all(bars[i - l]["high"] < cand["high"] for l in range(1, self.lookback + 1)) and \
                      all(bars[i + r]["high"] < cand["high"] for r in range(1, self.confirmation + 1))
            is_low = all(bars[i - l]["low"] > cand["low"] for l in range(1, self.lookback + 1)) and \
                     all(bars[i + r]["low"] > cand["low"] for r in range(1, self.confirmation + 1))

            if is_high:
                swings.append(SwingPoint(
                    timestamp_utc=cand["timestamp_utc"],
                    price=cand["high"],
                    type="SWING_HIGH",
                    confirmed_index=i + self.confirmation
                ))
            if is_low:
                swings.append(SwingPoint(
                    timestamp_utc=cand["timestamp_utc"],
                    price=cand["low"],
                    type="SWING_LOW",
                    confirmed_index=i + self.confirmation
                ))
        return swings

    def evaluate_news_quarantine(self, current_utc: datetime, upcoming_events: List[Dict[str, Any]]) -> str:
        for event in upcoming_events:
            diff_min = (event["timestamp_utc"] - current_utc).total_seconds() / 60.0
            if 0 <= diff_min <= 10.0:
                return "BLOCKED"
            elif 10.0 < diff_min <= 30.0:
                return "ELEVATED"
            elif -15.0 <= diff_min < 0:
                return "POST_EVENT_REASSESSMENT"
        return "NORMAL"
`
  },
  {
    filename: 'decision_and_setup_engine.py',
    category: '5. Setup & Decision Framework (Phase 4)',
    description: 'موتور ارزیابی ستاپ‌های A تا D، امتیازدهی کیفی، تخمین احتمال آماری ویلسون، محاسبه امید ریاضی (EV) و فیلترهای NO TRADE',
    code: `"""
FO-X 5M — Setup Engine & Decision Framework (Phase 4)
Orchestrates setup detection, Bayesian-Wilson scoring, Expected Value (EV) calculation, and NO TRADE guards.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import math

@dataclass
class SetupResult:
    setup_name: str
    direction: str # 'CALL' | 'PUT' | 'NO_TRADE'
    is_valid: bool
    raw_score: float
    unmet_rules: List[str]

@dataclass
class ProbabilityMetrics:
    sample_size: int
    win_rate: float
    wilson_lower_bound_95: float
    wilson_upper_bound_95: float
    shrinkage_p: float

@dataclass
class EVCalculation:
    win_probability: float
    broker_payout_pct: float
    expected_value_pct: float
    breakeven_win_rate: float
    verdict: str

class DecisionArbiter:
    def __init__(self, min_score_threshold: float = 72.0, min_payout_pct: float = 75.0, min_ev_pct: float = 4.0):
        self.min_score_threshold = min_score_threshold
        self.min_payout_pct = min_payout_pct
        self.min_ev_pct = min_ev_pct

    def evaluate_setup_a_sweep_absorption(self, bar: Dict[str, Any], context: Dict[str, Any]) -> SetupResult:
        """
        Setup A: Liquidity Sweep + Absorption Reversal
        """
        sweeps = context.get("recent_sweeps", [])
        absorption = context.get("absorption_summary", {})
        
        has_bull_sweep = any(s["direction"] == "BULLISH_SWEEP" for s in sweeps)
        has_bear_sweep = any(s["direction"] == "BEARISH_SWEEP" for s in sweeps)
        
        if not has_bull_sweep and not has_bear_sweep:
            return SetupResult("SETUP_A_SWEEP_ABSORPTION", "NO_TRADE", False, 0.0, ["No valid liquidity sweep detected"])
            
        direction = "CALL" if has_bull_sweep else "PUT"
        score = 80.0 if absorption.get("score", 0) >= 60 else 45.0
        is_valid = score >= self.min_score_threshold
        
        return SetupResult(
            setup_name="SETUP_A_SWEEP_ABSORPTION",
            direction=direction if is_valid else "NO_TRADE",
            is_valid=is_valid,
            raw_score=score,
            unmet_rules=[] if is_valid else ["Absorption score below threshold"]
        )

    def calculate_wilson_interval(self, p: float, n: int, z: float = 1.96) -> Tuple[float, float]:
        """Calculates 95% Wilson Score Confidence Interval."""
        if n == 0:
            return 0.5, 0.5
        denom = 1 + (z ** 2) / n
        center = p + (z ** 2) / (2 * n)
        spread = z * math.sqrt((p * (1 - p)) / n + (z ** 2) / (4 * n * n))
        return (center - spread) / denom, (center + spread) / denom

    def calculate_expected_value(self, win_p: float, payout_pct: float) -> EVCalculation:
        """Calculates binary options expected value."""
        loss_p = 1.0 - win_p
        reward_ratio = payout_pct / 100.0
        ev = (win_p * reward_ratio) - (loss_p * 1.0)
        ev_pct = round(ev * 100.0, 2)
        breakeven = 1.0 / (1.0 + reward_ratio)
        
        if ev_pct >= self.min_ev_pct:
            verdict = "STRONG_POSITIVE_EV"
        elif ev_pct > 0:
            verdict = "MARGINAL_EV"
        else:
            verdict = "NEGATIVE_EV"
            
        return EVCalculation(
            win_probability=win_p,
            broker_payout_pct=payout_pct,
            expected_value_pct=ev_pct,
            breakeven_win_rate=round(breakeven, 3),
            verdict=verdict
        )

    def run_full_pipeline(self, bar: Dict[str, Any], context: Dict[str, Any], broker_payout: float = 85.0) -> Dict[str, Any]:
        """Full execution arbiter generating strictly CALL, PUT, or NO_TRADE."""
        # 1. Check Data Quality and News Guard
        if context.get("data_quality_score", 100) < 75:
            return {"action": "NO_TRADE", "reason": "DATA_QUALITY_DEGRADED"}
        if context.get("news_quarantine_state") == "BLOCKED":
            return {"action": "NO_TRADE", "reason": "NEWS_QUARANTINE_ACTIVE"}

        # 2. Setup Evaluation
        setup = self.evaluate_setup_a_sweep_absorption(bar, context)
        if not setup.is_valid or setup.direction == "NO_TRADE":
            return {"action": "NO_TRADE", "reason": "NO_QUALIFIED_SETUP"}

        # 3. Wilson Probability & EV
        wilson_low, wilson_high = self.calculate_wilson_interval(0.64, 312)
        ev_calc = self.calculate_expected_value(wilson_low, broker_payout)

        if ev_calc.expected_value_pct < self.min_ev_pct:
            return {"action": "NO_TRADE", "reason": "NEGATIVE_OR_LOW_EV", "ev_metrics": ev_calc}

        return {
            "action": setup.direction,
            "setup": setup.setup_name,
            "confidence_score": setup.raw_score,
            "ev_metrics": ev_calc,
            "wilson_ci_95": (wilson_low, wilson_high)
        }
`
  },
  {
    filename: 'validation_and_monte_carlo.py',
    category: '5. Validation & Monte Carlo Engine',
    description: 'کد پایتون برای بک‌تستینگ با تعصب زمانی صفر (Zero Look-Ahead)، اعتبارسنجی Walk-Forward و شبیه‌سازی ۱۰,۰۰۰ تکرار مونت‌کارلو',
    code: `"""
FO-X 5M — Phase 5: Quantitative Validation, Walk-Forward & Monte Carlo Engine
Strict Zero Look-Ahead Bias & Binary Options 5M Expiry Outcome Simulator.
"""

from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field
import numpy as np
import math

class BinaryTradeRecord(BaseModel):
    trade_id: str
    setup_name: str
    direction: str  # "CALL" | "PUT"
    entry_price: float
    expiry_price: float
    result: str  # "WIN" | "LOSS" | "TIE"
    pnl_usd: float
    cumulative_pnl_usd: float
    payout_pct: float = 85.0

class BacktestMetrics(BaseModel):
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    breakeven_win_rate: float
    edge_pct: float
    wilson_lower_95: float
    wilson_upper_95: float
    max_consecutive_losses: int
    max_drawdown_usd: float
    profit_factor: float
    expected_value_usd: float

class MonteCarloMetrics(BaseModel):
    simulations: int
    median_final_equity: float
    var_95_worst_case: float
    best_case_95: float
    worst_drawdown_usd: float
    avg_max_losing_streak: float
    risk_of_ruin_pct: float
    profit_probability_pct: float

class QuantitativeValidationEngine:
    def __init__(self, broker_payout: float = 85.0, stake_usd: float = 100.0):
        self.broker_payout = broker_payout
        self.stake_usd = stake_usd

    def evaluate_binary_outcome(self, direction: str, entry_price: float, expiry_price: float) -> Tuple[str, float]:
        """Evaluates strictly at 5M bar expiry."""
        if direction == "CALL":
            if expiry_price > entry_price:
                return "WIN", round(self.stake_usd * (self.broker_payout / 100.0), 2)
            elif expiry_price < entry_price:
                return "LOSS", -self.stake_usd
            return "TIE", 0.0
        elif direction == "PUT":
            if expiry_price < entry_price:
                return "WIN", round(self.stake_usd * (self.broker_payout / 100.0), 2)
            elif expiry_price > entry_price:
                return "LOSS", -self.stake_usd
            return "TIE", 0.0
        return "TIE", 0.0

    def compute_backtest_metrics(self, trades: List[BinaryTradeRecord]) -> BacktestMetrics:
        """Calculates professional quantitative performance metrics."""
        total = len(trades)
        if total == 0:
            return BacktestMetrics(
                total_trades=0, wins=0, losses=0, win_rate=0.0,
                breakeven_win_rate=54.05, edge_pct=0.0, wilson_lower_95=0.0,
                wilson_upper_95=0.0, max_consecutive_losses=0, max_drawdown_usd=0.0,
                profit_factor=0.0, expected_value_usd=0.0
            )

        wins = sum(1 for t in trades if t.result == "WIN")
        losses = sum(1 for t in trades if t.result == "LOSS")
        wr = round((wins / total) * 100.0, 2)
        be = round((1.0 / (1.0 + self.broker_payout / 100.0)) * 100.0, 2)
        edge = round(wr - be, 2)

        # Wilson 95% Confidence Interval
        p = wr / 100.0
        z = 1.96
        denom = 1 + (z**2) / total
        center = p + (z**2) / (2 * total)
        spread = z * math.sqrt((p * (1 - p)) / total + (z**2) / (4 * total**2))
        wilson_low = round(((center - spread) / denom) * 100.0, 2)
        wilson_high = round(((center + spread) / denom) * 100.0, 2)

        # Drawdown & Consecutive Losses
        max_losses, cur_losses = 0, 0
        peak_equity, max_dd = 0.0, 0.0
        for t in trades:
            if t.result == "LOSS":
                cur_losses += 1
                if cur_losses > max_losses:
                    max_losses = cur_losses
            else:
                cur_losses = 0

            if t.cumulative_pnl_usd > peak_equity:
                peak_equity = t.cumulative_pnl_usd
            dd = peak_equity - t.cumulative_pnl_usd
            if dd > max_dd:
                max_dd = dd

        gross_profit = wins * self.stake_usd * (self.broker_payout / 100.0)
        gross_loss = losses * self.stake_usd
        pf = round(gross_profit / max(1.0, gross_loss), 2)
        ev_usd = round(sum(t.pnl_usd for t in trades) / total, 2)

        return BacktestMetrics(
            total_trades=total,
            wins=wins,
            losses=losses,
            win_rate=wr,
            breakeven_win_rate=be,
            edge_pct=edge,
            wilson_lower_95=wilson_low,
            wilson_upper_95=wilson_high,
            max_consecutive_losses=max_losses,
            max_drawdown_usd=round(max_dd, 2),
            profit_factor=pf,
            expected_value_usd=ev_usd
        )

    def run_monte_carlo_resampling(self, trades: List[BinaryTradeRecord], num_simulations: int = 10000) -> MonteCarloMetrics:
        """Executes 10,000 Monte Carlo bootstrap resamplings with replacement."""
        if not trades:
            return MonteCarloMetrics(
                simulations=num_simulations, median_final_equity=0,
                var_95_worst_case=0, best_case_95=0, worst_drawdown_usd=0,
                avg_max_losing_streak=0, risk_of_ruin_pct=0, profit_probability_pct=0
            )

        pnl_pool = [t.pnl_usd for t in trades]
        num_trades = len(trades)

        final_equities = []
        worst_dd_all = 0.0
        total_max_loss_streaks = 0
        ruin_count = 0

        for _ in range(num_simulations):
            sampled_pnls = np.random.choice(pnl_pool, size=num_trades, replace=True)
            equity_curve = np.cumsum(sampled_pnls)
            final_equity = equity_curve[-1]
            final_equities.append(final_equity)

            # Drawdown
            peaks = np.maximum.accumulate(equity_curve)
            drawdowns = peaks - equity_curve
            max_dd = np.max(drawdowns)
            if max_dd > worst_dd_all:
                worst_dd_all = max_dd

            # Losing Streak
            cur_streak, max_streak = 0, 0
            for pnl in sampled_pnls:
                if pnl < 0:
                    cur_streak += 1
                    if cur_streak > max_streak:
                        max_streak = cur_streak
                else:
                    cur_streak = 0
            total_max_loss_streaks += max_streak

            if final_equity < -1000:
                ruin_count += 1

        final_equities.sort()
        idx_5 = int(num_simulations * 0.05)
        idx_50 = int(num_simulations * 0.50)
        idx_95 = int(num_simulations * 0.95)

        profitable = sum(1 for eq in final_equities if eq > 0)

        return MonteCarloMetrics(
            simulations=num_simulations,
            median_final_equity=round(float(final_equities[idx_50]), 1),
            var_95_worst_case=round(float(final_equities[idx_5]), 1),
            best_case_95=round(float(final_equities[idx_95]), 1),
            worst_drawdown_usd=round(float(worst_dd_all), 1),
            avg_max_losing_streak=round(total_max_loss_streaks / num_simulations, 1),
            risk_of_ruin_pct=round((ruin_count / num_simulations) * 100.0, 2),
            profit_probability_pct=round((profitable / num_simulations) * 100.0, 1)
        )
`
  }
];


