# FO-X 5M — Footprint Engine Architecture & Technical Documentation

## ۱. نمای کلی و فلسفه ریزساختار (Overview & Philosophy)
موتور فوت‌پرینت (**Footprint Engine**) هسته مرکزی تحلیل جریان سفارشات (Order Flow) در سامانه FO-X 5M است. این موتور جریان تیک‌های اعتبارسنجی‌شده را به بارهای ساختاریافته ۵ دقیقه‌ای شامل توزیع دقیق حجم در لول‌های گسسته قیمت (**Price Ladder**)، دلتای خریداران و فروشندگان مهاجم، و دلتای تجمعی نشست معاملاتی (**Session CVD**) تبدیل می‌کند.

---

## ۲. اصول و قوانین تغییرناپذیر مهندسی (Strict Non-Negotiable Rules)

1. **عدم حدس حجم معاملاتی:** اگر تیک ورودی فاقد مظنه‌های واقعی Bid و Ask باشد، جهت معامله `UNKNOWN` ثبت شده و کیفیت بار به `DEGRADED` تغییر می‌یابد. بازسازی فوت‌پرینت از کندل‌های OHLC مطلقاً ممنوع است.
2. **عدم هاردکد کردن مشخصات ابزار:** سایز تیک (`tick_size`) و تعداد اعشار (`price_precision`) برای هر نماد منحصراً از فایل پیکربندی `configs/orderflow_config.yaml` خوانده می‌شوند.
3. **تطابق ۱۰۰٪ در پردازش زنده و بازپخش تاریخی (Live/Replay Exact Parity):** بر اساس آزمون‌های خودکار، پردازش تیک‌به‌تیک زنده و پردازش دسته‌ای بازپخش تاریخی برای توالی تیک یکسان، خروجی‌های کاملاً یکسان و بایتی برابر از `FootprintBar` تولید می‌کنند.
4. **مرزبندی زمانی دقیق:** مرزهای زمانی بارها با محاسبه کف زمانی (`Floor Timestamp`) در بازه باز-بسته $[T_{start}, T_{end})$ بدون هرگونه نشت دیتای آینده (No Look-Ahead Bias) مدیریت می‌شوند.

---

## ۳. جریان داده و پایپ‌لاین فوت‌پرینت (Footprint Processing Flow)

```text
               [ Validated Market Ticks Stream ]
                               ↓
  [ TradeClassifier (Quote-Rule / Lee-Ready aggressor detection) ]
        ├── BUY (Executed at/above Ask)
        ├── SELL (Executed at/below Bid)
        └── UNKNOWN (Bid/Ask unavailable - No guessing)
                               ↓
  [ BarAggregator (Epoch floor [09:00, 09:05) time windows) ]
                               ↓
  [ PriceLadder (Discretized Volume Accumulator on Tick Grid) ]
        ├── Price Level [Bid Vol x Ask Vol]
        ├── Net Price Delta (Ask_Vol - Bid_Vol)
        └── Point of Control (POC - Level with max volume)
                               ↓
  [ DeltaCalculator (Bar Delta, Min/Max Delta Excursions, Delta %) ]
                               ↓
  [ CVDEngine (Session CVD with Asia / London / NY auto-reset) ]
                               ↓
             [ FootprintBar & CVDPoint Entities ]
                               ↓
  [ FootprintStorage (Date-partitioned Snappy Parquet Archives) ]
        ├── /data/footprint/bars/{SYMBOL}/YYYY-MM-DD.parquet
        ├── /data/footprint/levels/{SYMBOL}/YYYY-MM-DD.parquet
        └── /data/footprint/cvd/{SYMBOL}/YYYY-MM-DD.parquet
```

---

## ۴. اجزای اصلی فاز ۹ (Core Components)

### ۴.۱. مدل‌های فوت‌پرینت (`app/models/footprint.py`)
- `PriceLevel`: حاوی قیمت، حجم Bid، حجم Ask، حجم Unknown، مجموع حجم و دلتای لول.
- `FootprintBar`: تجمیع کامل OHLC، لدر سطوح، POC، دلتای بار، اکستریم‌های دلتا و وضعیت سلامت داده (`FootprintQuality`).
- `CVDPoint`: نقطه سری زمانی دلتای تجمعی متصل به نشست فعال معاملاتی.

### ۴.۲. طبقه‌بندی‌کننده معاملات (`app/footprint_engine/trade_classifier.py`)
- استنتاج جهت خریدار یا فروشنده مهاجم بدون حدس؛ در غیاب داده‌های بوک، وضعیت `UNKNOWN` برمی‌گرداند.

### ۴.۳. نردبان قیمت (`app/footprint_engine/price_ladder.py`)
- رندسازی دقیق قیمت‌ها با کلاس `Decimal` روی گرید سایز تیک ابزار (مثلاً $0.1$ برای طلای کامکس GC و $0.01$ برای طلای نقدی XAUUSD).

### ۴.۴. موتور دلتای تجمعی نشست (`app/footprint_engine/cvd_engine.py`)
- محاسبه پیوسته دلتای تجمعی نشست‌های آسیا، لندن، نیویورک و پست‌مارکت با ریست در نقاط گردش نشست بر اساس ساعات کانفیگ.

### ۴.۵. ذخیره‌سازی ستونی Parquet (`app/footprint_engine/storage.py`)
- ذخیره‌سازی مجزا و فشرده بارها، لدر لول‌های قیمتی و نقاط CVD با قابلیت کوئری مستقیم DuckDB.

---

## ۵. تحلیل و بهینه‌سازی کارایی (Performance & Scalability)
* **مدیریت حافظه در تیک‌های میلیونی:** استفاده از ساختار سبک دیکشنری برای سطوح قیمت داخل هر بار و خروج سریع از حافظه پس از ذخیره دسته‌ای در Parquet.
* **بهینه‌سازی‌های آتی (Next Phases):** در صورت افزایش بار داده به بیش از ۱۰ هزار تیک در ثانیه، تبدیل محاسبات نردبان قیمت به آرایه‌های ساختاریافته NumPy/Numba پیشنهاد می‌گردد.
