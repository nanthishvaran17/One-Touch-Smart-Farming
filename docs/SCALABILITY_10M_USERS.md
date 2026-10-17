# Farm Saathi — Architecture & Capacity Plan for 10 Million Users

This document provides the capacity modeling, architecture blueprint, and load testing strategy for scaling **Farm Saathi** from regional pilot to 10 million registered farmers.

---

## 1. Capacity Modeling & Traffic Estimates

For **10,000,000 registered farmers**:

| Metric | Estimated Value | Calculation Basis |
| :--- | :--- | :--- |
| **Active Daily Farmers (DAU)** | 2,500,000 (25%) | Daily morning & evening irrigation checks |
| **Peak Concurrent Users (CCU)** | 400,000 | Concentrated between 05:30–08:30 AM & 05:00–08:00 PM |
| **Registered Motors** | 15,000,000 | ~1.5 motors per farm (borewell, lift, drip) |
| **Simultaneously Active Controllers** | 1,200,000 | During irrigation windows |
| **Telemetry Ingestion Rate** | 20,000 msgs/sec | Dynamic heartbeat: 10s during RUNNING, 60s when IDLE |
| **Peak Command Throughput** | 8,000 commands/sec | Mass start/stop during power supply restoration |
| **Database Daily Ingestion Volume** | ~45 GB / day compressed | Raw telemetry downsampled to 5-min intervals for historical cold storage |

---

## 2. Recommended Scaled Architecture

```
[ Farmer Mobile / Web Clients ]
             │
   HTTPS / WSS (Cloudflare Edge / CDN)
             │
┌────────────▼────────────────────────┐
│      Application Load Balancer      │
└────────────┬────────────────────────┘
             │
   ┌─────────┴─────────┐
   ▼                   ▼
┌─────────────────────────────────────┐
│  Stateless FastAPI API Cluster      │ (Autoscaling K8s pods: 40-120 replicas)
└──────────┬─────────────────┬────────┘
           │                 │
    Token Validation    Commands & Telemetry
           │                 │
┌──────────▼─────────┐ ┌─────▼────────────────────────┐
│ Redis Cluster      │ │ Apache Kafka / AWS Kinesis   │
│ (Sessions & Cache) │ │ Telemetry & Command Stream   │
└────────────────────┘ └─────┬────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌────────────────────────┐      ┌─────────────────────────┐
│ TimescaleDB / ClickHouse│     │ PostgreSQL Primary      │
│ (High-Volume Telemetry)│      │ (Authoritative Relational)│
└────────────────────────┘      │ - Users, Farms, Motors  │
                                │ - Read Replicas (x4)    │
                                └─────────────────────────┘
```

---

## 3. High-Throughput IoT Messaging Layer

- **Managed MQTT Broker**: HiveMQ Enterprise or AWS IoT Core with TLS 1.3 mutual authentication (mTLS) via X.509 device certificates.
- **Topic Partitions**:
  - `farms/{farm_id}/devices/{device_id}/telemetry`
  - `farms/{farm_id}/devices/{device_id}/commands`
  - `farms/{farm_id}/devices/{device_id}/acks`
- **Backpressure & Reconnect Storm Mitigation**:
  - Exponential backoff with jitter on controller reconnects (prevents thundering herd when three-phase rural electricity grid turns ON).
  - Durable Redis/Kafka buffer to absorb peak bursts without exhausting PostgreSQL connection pools.

---

## 4. Database Partitioning & Archival

1. **Authoritative Relational Data**:
   - PostgreSQL (or Neon Serverless Postgres with autoscaling compute).
   - Read/write split: write commands hit Primary; read-only dashboard status hits Read Replicas.
   - Row-Level Security (RLS) ensures complete multi-tenant tenant isolation by `farm_id`.

2. **Telemetry Data Retention**:
   - Hot tier (last 7 days): In-memory cache & TimescaleDB hypertable partitioned by week.
   - Warm tier (8 to 90 days): Compressed columnar chunks for monthly power and runtime reports.
   - Cold tier (> 90 days): Parquet export to GCS / S3 Glacier with lifecycle expiration.

---

## 5. Load Testing Verification

A dedicated Locust benchmark script is provided at `backend/tests/load_test_locust.py`.

To execute a local stress test:
```bash
locust -f backend/tests/load_test_locust.py --host=http://127.0.0.1:8000 --users=50 --spawn-rate=5
```
