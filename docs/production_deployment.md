# FO-X 5M — Production Deployment & Operations Manual

## 1. System Overview & Architecture

The **FO-X 5M Quantitative Engine** is architected for continuous 24/5 cloud operation.

```text
               ┌───────────────────────────────┐
               │    Cloud Server / Host VPS    │
               │   (Ubuntu 22.04 LTS / Debian) │
               └───────────────┬───────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌────────────────────────┐                   ┌────────────────────────┐
│  PostgreSQL (Docker)   │                   │  FO-X Engine (Docker)  │
│  - Port 5432           │                   │  - FastAPI REST / WS   │
│  - Persistent Volume   │                   │  - Orderflow Engine    │
│  - Migrations Applied  │                   │  - Port 8000           │
└────────────────────────┘                   └───────────┬────────────┘
                                                         │
                                                         ▼
                                             ┌────────────────────────┐
                                             │ Quant Terminal (React) │
                                             │  - Port 3000           │
                                             │  - Real-Time Watchdog  │
                                             └────────────────────────┘
```

---

## 2. Server Requirements

- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, or RHEL 9+)
- **CPU**: 4+ Cores (for low latency tick normalization and footprint calculations)
- **RAM**: 8 GB minimum (16 GB recommended for multi-day in-memory footprint buffers)
- **Storage**: 50 GB SSD / NVMe (High IOPS for tick logging)

---

## 3. Quick Deployment (Docker Compose)

```bash
# 1. Clone repository
git clone https://github.com/company/fox-5m.git /opt/fox_trading
cd /opt/fox_trading

# 2. Configure environment
cp .env.example .env
nano .env

# 3. Launch with automated deployment script
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

---

## 4. Verification & Health Probes

```bash
# Check overall system readiness
curl -s http://localhost:8000/health
```

Expected JSON response:
```json
{
  "status": "HEALTHY",
  "timestamp": "2026-08-30T10:00:00Z",
  "environment": "production",
  "services": {
    "database": { "status": "HEALTHY", "latency_ms": 1.2 },
    "market_data_feed": { "status": "HEALTHY", "latency_ms": 3.5 },
    "orderflow_engine": { "status": "HEALTHY", "latency_ms": 0.8 },
    "paper_trading_service": { "status": "HEALTHY", "latency_ms": 0.4 }
  }
}
```

---

## 5. Daily Backup & Retention

The snapshot backup script runs automatically and retains the last 14 days of snapshots:
```bash
# Manual snapshot creation
python -c "from app.core.backup import ProductionBackupManager; print(ProductionBackupManager().create_snapshot_backup())"
```
