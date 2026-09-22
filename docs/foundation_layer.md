# FO-X 5M — Foundation Layer Architecture & Technical Documentation

## ۱. نمای کلی سیستم (System Overview)
سیستم **FO-X 5M** یک موتور کمّی و پردازش هوشمند جریان سفارشات (Order Flow) بر بستر طلای جهانی (GC Futures / XAUUSD) برای افق زمانی ۵ دقیقه است. این لایه بنیادین، پایداری نوع داده‌ها، اعتبارسنجی ورودی‌ها، پیکربندی ایزوله و لاگینگ ساختاریافته را بر اساس استانداردهای **Python 3.12** و **Pydantic v2** تضمین می‌کند.

---

## ۲. جریان پیکربندی (Configuration Flow)
- **مرجع تنظیمات:** فایل `configs/base_config.yaml` مقادیر پیش‌فرض امن را برای بخش‌های `app`، `logging`، `database`، `data` و `research` فراهم می‌کند.
- **بازنویسی از متغیرهای محیطی:** تمام فیلدها با پیشوند `FOX_` قابل بازنویسی هستند (مانند `FOX_APP__DEBUG=true`).
- **دسترسی ایزوله:** از طریق تابع `get_config()` به صورت Singleton و بدون متغیرهای Hardcoded در دسترس است.

---

## ۳. سیستم لاگینگ ساختاریافته (Structured Logging)
- **موتور:** کتابخانه `Loguru`
- **قابلیت‌ها:**
  - تفکیک لاگ‌های کنسول با رنگ‌بندی و فرمت زمان دقیق میلی‌ثانیه‌ای UTC.
  - ثبت لاگ‌های چرخشی (Rotation) در مسیر `logs/fox5m.log` با آرشیو خودکار.
  - متد کمکی `log_event()` برای ارسال رویدادهای ساختاریافته همراه با Payload داده‌ای.

---

## ۴. مدل‌های دامنه داده (Core Domain Models)
1. **`Tick` (`app/models/tick.py`):** مدل اتمیک تیک‌های معاملاتی شامل قیمت، حجم، Best Bid/Ask، جهت مهاجم (`TradeSide.BUY`/`SELL`) و اعتبارسنجی اسپرِد.
2. **`FootprintLevel` & `FootprintBar` (`app/models/footprint.py`):** مدل‌های کندل فوت‌پرینت ۵ دقیقه‌ای شامل توزیع لول‌به‌لول حجم Bid/Ask، دلتا، اکستریم‌های دلتا و اعتبارسنجی OHLC.
3. **`FeatureBase` & Subclasses (`app/models/orderflow_features.py`):** ساختارهای داده برای دلتای نواری، عدم‌تعادل‌های قطری (`DiagonalImbalance`)، جذب حجم و فرسودگی.
4. **`MarketContext` (`app/models/market_context.py`):** ارزیابی بافتار چند تایم‌فریمی شامل رژیم، ساختار بازار (BOS/MSS/Sweep)، سشن معاملاتی و قرنطینه خبری.
5. **`Setup` & `Decision` (`app/models/decision.py`):** فرمت ستاپ‌های A تا D، امتیاز کیفی، برآورد احتمال، کران پایین ویلسون و خروجی تصمیم نهایی (`CALL`, `PUT`, `NO_TRADE`).
6. **`TradeResult` (`app/models/trade_result.py`):** سوابق تسویه و اعتبارسنجی ریاضی سود/زیان باینری آپشن ۵ دقیقه.

---

## ۵. استراتژی تست و اعتبارسنجی (Testing Strategy)
- اجرای تست‌های واحد جامع در `tests/test_domain_models.py` و `tests/test_core_infrastructure.py`.
- اعتبارسنجی مقادیر منفی نامعتبر، اسپردهای معکوس، انحرافات OHLC و تناقضات PnL با استفاده از `pytest`.
