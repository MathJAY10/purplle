# Testing & Validation

This document describes the testing strategy and validation approach used to verify the correctness and reliability of the Retail Store Analytics Platform.

---

# Testing Strategy

The project uses a combination of:

1. Unit Tests
2. Integration Tests
3. End-to-End Validation

All automated tests are implemented using Pytest.

---

# Automated Test Coverage

## 1. Line Crossing Logic

File:

```text
test_line_crossing.py
```

Purpose:

* Verify ENTRY event generation
* Verify EXIT event generation
* Prevent duplicate events
* Validate crossing direction

Checks:

* Entry crossing creates ENTRY event
* Exit crossing creates EXIT event
* Hovering near line does not create duplicates

---

## 2. Database Persistence

File:

```text
test_db_persistence.py
```

Purpose:

Verify that processed events are stored correctly.

Checks:

* EventRecord creation
* SessionRecord creation
* Event-session linking
* Correct timestamps

---

## 3. Idempotency

File:

```text
test_idempotency.py
```

Purpose:

Ensure duplicate event processing does not create duplicate database records.

Checks:

* Same event processed multiple times
* Only one database record created
* Session consistency maintained

---

## 4. Analytics Validation

Files:

```text
test_metrics.py
test_anomalies.py
```

Purpose:

Verify analytics calculations.

Checks:

* Traffic metrics
* Occupancy calculations
* Conversion funnel calculations
* Anomaly detection logic

---

## 5. API Validation

Purpose:

Verify API correctness.

Checks:

* Endpoint responses
* Status codes
* Schema validation
* Analytics endpoints

---

# Running Tests

Run all tests:

```bash
docker compose run --rm api pytest
```

Expected Result:

```text
16 tests passed
```

---

# End-to-End Validation

The complete system was validated using real CCTV footage.

## Test Video

```text
CAM5.mp4
```

## Pipeline

CCTV Video
→ YOLOv8 Detection
→ ByteTrack Tracking
→ Entry/Exit Event Generation
→ Redis Streams
→ Worker Processing
→ PostgreSQL

---

## Validation Results

### Event Generation

```text
Events Generated = 10
```

### Event Distribution

```text
ENTRY = 6
EXIT  = 4
```

### Session Creation

```text
Sessions Created = 5
Active Sessions  = 4
Closed Sessions  = 1
```

### Redis Verification

```text
Redis Stream Length = 10
```

### PostgreSQL Verification

```text
Events Stored   = 10
Sessions Stored = 5
```

---

# Verified Components

✓ YOLOv8 Detection

✓ ByteTrack Tracking

✓ Entry / Exit Event Generation

✓ Redis Stream Publishing

✓ Worker Consumption

✓ PostgreSQL Persistence

✓ Session Lifecycle Management

✓ API Layer

---

# Outcome

PASS

The platform successfully processed CCTV footage, generated customer movement events, published them through Redis Streams, consumed them using background workers, and persisted customer sessions in PostgreSQL.

The complete event lifecycle from video ingestion to database persistence was validated successfully.
