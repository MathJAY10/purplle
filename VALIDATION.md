# Testing & Validation

## Testing Strategy

The project uses multiple testing layers:

1. Unit Testing
2. Integration Testing
3. End-to-End Validation

---

## Automated Tests

Executed using Pytest.

Results:

24/24 tests passed.

Covered Areas:

* Line Crossing Logic
* Event Persistence
* Session Management
* Queue Analytics
* Purchase Correlation
* Anomaly Detection
* Redis Integration
* POS Ingestion
* API Validation
* Idempotency

---

## End-to-End Validation

A real CCTV video was processed through the complete architecture.

Input:

CAM 5.mp4

Pipeline:

Video

↓

YOLOv8

↓

ByteTrack

↓

Event Generation

↓

Redis Streams

↓

Worker Processing

↓

PostgreSQL

---

## Validation Outcome

Verified:

✓ Detection Pipeline

✓ Tracking Pipeline

✓ Event Generation

✓ Redis Publishing

✓ Worker Consumption

✓ Database Persistence

✓ Session Lifecycle Management

✓ Analytics Processing

✓ API Availability

---

## Infrastructure Verification

Docker Services:

* API Healthy
* Worker Healthy
* PostgreSQL Healthy
* Redis Healthy

Migrations:

* Successfully Applied

Database:

* Events Persisted
* Sessions Persisted

Result:

PASS

The complete event lifecycle from video ingestion to analytics persistence was successfully validated.
