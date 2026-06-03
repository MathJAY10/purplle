# Retail Store Analytics Platform

A production-oriented computer vision platform that converts CCTV footage into actionable retail analytics. The system detects customer movement, tracks visitor journeys, measures queue behavior, correlates purchases, and identifies operational anomalies using an event-driven architecture.

---

## Problem Statement

Physical retail stores often lack visibility into customer behavior beyond POS transactions. Unlike e-commerce platforms, store operators cannot easily answer questions such as:

* How many visitors entered the store?
* How many visitors reached the billing counter?
* How many left without purchasing?
* When do queues become unusually large?
* Which store zones receive the most traffic?

This platform bridges that gap by transforming CCTV footage into structured business events and analytics.

---

## Key Features

### Computer Vision

* YOLOv8 Person Detection
* ByteTrack Multi-Object Tracking
* Visitor Re-Identification
* Staff Detection
* Entry and Exit Detection
* Zone Tracking

### Event Processing

* Redis Streams Event Pipeline
* Consumer Group Based Processing
* Idempotent Event Handling
* Session Lifecycle Management
* Event Persistence

### Analytics

* Traffic Analytics
* Occupancy Analytics
* Queue Analytics
* Purchase Funnel Analytics
* Conversion Tracking
* Anomaly Detection

### POS Integration

* CSV Transaction Upload
* Timezone Safe Processing
* Purchase Attribution Engine

---

## System Flow

CCTV Video

↓

YOLOv8 Detection

↓

ByteTrack Tracking

↓

Business Event Generation

↓

Redis Streams

↓

Worker Processing

↓

PostgreSQL

↓

Analytics APIs

---

## Technology Stack

### Computer Vision

* YOLOv8
* ByteTrack
* OpenCV

### Backend

* FastAPI
* Python 3.11+
* SQLAlchemy
* Alembic

### Infrastructure

* PostgreSQL
* Redis Streams
* Docker
* Docker Compose

### Testing

* Pytest

---

## Validation Results

### Automated Testing

* 24/24 tests passed

### Real CCTV Validation

Input Video:

* CAM 5.mp4

Validated Flow:

Video → Detection → Tracking → Redis → Worker → PostgreSQL

Observed Results:

* Events persisted successfully
* Sessions created successfully
* Worker consumed Redis stream correctly
* Analytics services executed successfully

### Infrastructure Validation

* API Container Healthy
* Worker Container Healthy
* PostgreSQL Healthy
* Redis Healthy

---

## Production Hardening

The platform includes several safeguards commonly used in production systems:

* Event Idempotency
* Duplicate Processing Protection
* Session Lifecycle Validation
* Queue State Recovery
* Timezone Normalization
* Redis Consumer Groups
* Worker Retry Safety
* Database Constraints

---

## Future Improvements

* Multi-camera tracking
* Cross-camera re-identification
* Real-time dashboard
* Heatmap generation
* Predictive staffing recommendations
* Cloud deployment

---

## Conclusion

The platform demonstrates how computer vision, event-driven processing, and analytical modeling can be combined to deliver actionable retail intelligence from existing CCTV infrastructure.
