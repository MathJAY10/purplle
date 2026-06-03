# System Architecture

## Architectural Style

The system follows a Modular Monolith architecture.

The application is deployed as a single system but organized into independent modules with clearly defined responsibilities.

This approach provides:

* Faster development
* Easier testing
* Lower operational complexity
* Strong internal boundaries

without introducing the overhead of microservices.

---

## High-Level Architecture

The system contains two major execution planes.

### 1. Vision & Ingestion Plane

Responsible for generating business events.

Components:

* Video Reader
* YOLOv8 Detector
* ByteTrack Tracker
* Re-Identification Engine
* Zone Tracker
* Event Generator

Output:

Retail Events published to Redis Streams.

---

### 2. Analytics & Persistence Plane

Responsible for processing and serving analytics.

Components:

* Redis Workers
* PostgreSQL
* Analytics Services
* FastAPI APIs

Output:

Business metrics and operational insights.

---

## Event Driven Design

The platform models customer activity as immutable business events.

Examples:

* ENTRY
* EXIT
* REENTRY
* ZONE_ENTER
* ZONE_EXIT
* ZONE_DWELL

Events are published to Redis Streams and processed asynchronously.

This keeps the computer vision pipeline independent from database latency.

---

## Why Redis Streams

Redis Streams provides:

* Ordered delivery
* Event buffering
* Consumer groups
* Horizontal scalability

It acts as a shock absorber between bursty computer vision workloads and slower database operations.

---

## Database Design

Core Tables:

### events

Stores all immutable business events.

### sessions

Stores visitor journeys and visit sessions.

### transactions

Stores POS purchases.

### anomalies

Stores detected operational anomalies.

### metrics_cache

Stores precomputed analytical results.

---

## Analytics Modules

### Traffic Analytics

Measures store entries and exits.

### Queue Analytics

Measures queue size, wait times, and abandonment.

### Purchase Correlation

Correlates billing activity with customer sessions.

### Funnel Analytics

Tracks visitor conversion across store stages.

### Anomaly Detection

Detects unusual operational patterns using historical baselines.

---

## Scalability Strategy

The architecture scales independently across three dimensions:

### CV Processing

Additional inference workers.

### Stream Processing

Additional Redis consumers.

### API Layer

Additional FastAPI instances.

This separation prevents one workload from impacting another.
