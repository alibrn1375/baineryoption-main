# FO-X 5M — Market Data Layer Architecture & Technical Documentation

## ۱. نمای کلی (Overview)
لایه داده (**Data Layer**) مسئولیت دریافت، اعتبارسنجی کیفی، نرمال‌سازی و ذخیره‌سازی تیک‌های لحظه‌ای و تاریخی طلا را برای جفت‌ارز **XAU/USD** و قرارداد آتی طلای کامکس (**GC Futures**) بر عهده دارد. تمام داده‌ها پیش از ورود به موتورهای تحلیلی، مراحل سخت‌گیرانه اعتبارسنجی را طی می‌کنند.

---

## ۲. دیاگرام معماری پردازش داده (Pipeline Flow)

```text
  [ Historical / Live Data Source ]
                 ↓
  [ Abstract Provider Interface (HistoricalDataProvider / LiveDataProvider) ]
                 ↓
       [ Raw Tick Dictionary ]
                 ↓
   [ TickValidator ] ──(Invalid)──> [ Loguru Alert & DataQualityMonitor ]
          │
      (Valid)
          ↓
  [ TickNormalizer ] ──> Unified Pydantic Tick Model
          ↓
   [ Storage Layer ]
     ├── ParquetStorage (Date-partitioned Snappy files: /data/ticks/{SYMBOL}/YYYY-MM-DD.parquet)
     └── DuckDBAnalytics (In-process high-speed analytical SQL queries on Parquet)
```

---

## ۳. اجزای اصلی ماژول (Core Components)

### ۳.۱. اینترفیس‌های ارائه‌دهنده داده (`interfaces.py`)
- `HistoricalDataProvider`: خواندن داده‌های تاریخی بدون ایجاد Look-Ahead Bias.
- `LiveDataProvider`: جریان داده‌های بلادرنگ با قابلیت اتصال مجدد خودکار.
- `DataSourceMetadata`: متادیتای ساختاریافته منبع شامل نماد، تایم‌زون، نوع تیک و بازه زمانی.

### ۳.۲. موتور اعتبارسنجی تیک‌ها (`tick_validator.py`)
- بررسی مثبت بودن قیمت (`Price > 0`).
- کشف جهش‌های قیمتی غیرمنطقی تک‌تیک (> 5%).
- رد بوک‌های معکوس یا Crossed (`Ask < Bid`).
- کشف تیک‌های خارج از ترتیب زمانی (Out-of-order ticks) و پرش‌های تاریخی.

### ۳.۳. موتور نرمال‌سازی داده‌ها (`tick_normalizer.py`)
- نگاشت نمادهای ناهمگن به نمادهای استاندارد (`XAUUSD`, `GC_FUT`).
- تبدیل فرمت‌های گوناگون زمان به `datetime` با تایم‌زون قطعی `UTC`.
- استنتاج جهت سفارش مهاجم (`TradeSide.BUY` / `SELL`) با الگوریتم Lee-Ready.

### ۳.۴. ذخیره‌سازی ستونی Parquet و DuckDB (`parquet_storage.py` & `database.py`)
- **چرا Parquet؟** فشرده‌سازی بالا (Snappy)، سرعت لود چندبرابری نسبت به CSV و خواندن فقط ستون‌های مورد نیاز در حافظه.
- **DuckDB:** اجرای مستقیم کوئری‌های SQL بر روی فایل‌های پارکت بدون نیاز به راه‌اندازی سرور دیتابیس جداگانه.

---

## ۴. نتایج و پوشش آزمون‌ها (Test Suite)
تست‌های پیاده‌سازی‌شده در `tests/test_data_layer.py`:
- تایید اعتبارسنجی تیک سالم، رد قیمت منفی، رد بوک وارونه، و کشف زمان‌های جابه‌جا.
- تست نرمالایزر و تشخیص صحیح طرف مهاجم.
- تست رفت‌وبرگشت ذخیره‌سازی Parquet و کوئری تحلیلی DuckDB.
- تست پایپ‌لاین سراسری و ثبت لاگ کیفیت داده (`DataQualityReport`).
