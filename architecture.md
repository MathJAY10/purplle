# Store Intelligence System Architecture

## Purpose

This document explains the design decisions for a production-grade store intelligence platform that turns CCTV footage into structured retail events and analytics. The goal is to maximize maintainability, testability, and operational simplicity while still supporting a scalable event-driven pipeline.

## High-Level Architecture

The system is a modular monolith with two clear execution planes:

1. Ingestion and vision plane
   - Reads CCTV video from store cameras.
   - Runs human detection through a detector port.
   - Runs tracking through a tracker port.
   - Converts trajectories into business events.
   - Publishes events to Redis Streams.

2. Analytics and persistence plane
   - Consumes Redis Stream events in workers.
   - Persists canonical events and derived records to PostgreSQL.
   - Builds materialized read models for API queries.
   - Serves FastAPI endpoints for health and analytics reads.

This separation keeps the video pipeline independent from HTTP traffic and database latency.

## Why Redis

Redis Streams is the right message backbone for this challenge because the workload is moderate, event ordering matters, and operational simplicity is important.

### Why it fits

- Redis Streams gives append-only event buffering with ordered delivery.
- Consumer groups allow workers to scale horizontally without changing the producer.
- It is simpler to run in Docker Compose than Kafka.
- It is good enough for a challenge-scale retail pipeline where the main goal is reliable decoupling, not deep streaming infrastructure.
- It reduces coupling between the CV pipeline and persistence services.

### Why not Kafka here

- Kafka adds operational overhead that is not justified for the scope.
- It requires more cluster management, tuning, and local setup complexity.
- The challenge benefits more from fast delivery and maintainability than from enterprise-scale stream guarantees.

### Design consequence

Redis becomes the shock absorber between bursty inference output and slower downstream persistence. When the CV pipeline produces events faster than the API layer or database can consume them, Redis buffers the gap instead of blocking the detector loop.

## Why Modular Monolith

A modular monolith gives the best balance of speed, testability, and maintainability for this system.

### Why it fits

- The domain is cohesive: detection, tracking, event generation, persistence, and analytics all belong to one product boundary.
- The team can develop and test locally with one deployable artifact.
- Shared types and contracts stay inside the same codebase, which reduces serialization overhead and integration friction.
- It preserves a clean internal separation while avoiding microservice sprawl.

### Why not microservices

- Microservices would increase deployment complexity, observability overhead, and distributed failure modes.
- This challenge does not need independent organizational boundaries.
- A microservice split too early would slow delivery and make testing harder.

### Design consequence

The repository is structured as modules with explicit boundaries, not as one large import graph. That gives most of the maintainability benefit of services without the infrastructure penalty.

## Why Event-Driven

The domain is naturally event-driven because business meaning emerges from sequences of movement, zone visits, and dwell patterns.

### Why it fits

- CCTV inference produces a stream of observations, not a single final result.
- ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, dwell, and queue events are best modeled as immutable events.
- Event-driven design decouples detection from persistence and read models.
- It enables asynchronous processing, batching, retries, and backpressure handling.

### Design consequence

Instead of asking the CV pipeline to write directly to the database, the system publishes domain events first. Workers then consume and materialize those events into reporting tables and caches. This keeps inference latency low and avoids blocking the bottleneck path.

## Scalability Reasoning

The biggest scaling pressure is computer vision inference, not the API layer.

### Main bottlenecks

1. Frame decoding and video I/O
   - Raw MP4 or RTSP sources can be expensive to decode.
   - This should be isolated from the API process.

2. YOLOv8 inference
   - GPU or CPU inference is the primary throughput limit.
   - The detector must not be coupled to database writes.

3. Tracking over time
   - ByteTrack requires state across frames and careful batching.
   - It should stay in the CV pipeline only.

4. Database writes
   - If every frame caused synchronous writes, PostgreSQL would become a bottleneck.
   - Workers batch writes and materialize aggregates instead.

5. Read-heavy analytics queries
   - Funnel, heatmap, and anomaly endpoints can become expensive if computed on demand.
   - Precomputed metrics and indexes reduce query latency.

### How the design scales

- Scale inference workers independently from API workers.
- Use Redis Streams to buffer spikes and smooth out load.
- Keep FastAPI stateless so it can scale horizontally.
- Use PostgreSQL as the source of truth and metrics_cache for hot reads.
- Batch persistence operations in workers.
- Partition responsibilities so bottlenecks can be improved one by one.

### What scales first

- CV workers scale by adding more inference processes or GPU-backed nodes.
- Stream consumers scale by consumer group membership.
- API instances scale independently because they only read from storage.

## SOLID Usage

The system uses SOLID to keep the codebase extensible and safe to modify.

### Single Responsibility Principle

- Detector only detects.
- Tracker only tracks.
- EventPublisher only publishes.
- Repository only persists and retrieves.
- Services only orchestrate use cases.
- Workers only consume and process streams.

This keeps classes small and prevents god objects.

### Open/Closed Principle

- New detectors, trackers, or event types can be added without rewriting the core pipeline.
- Additional analytics endpoints can be built on top of existing read models.

### Liskov Substitution Principle

- Any implementation of Detector, Tracker, EventPublisher, or Repository should be swappable without breaking callers.
- This is important when future implementations move from mocks to YOLOv8 or from in-memory stores to PostgreSQL.

### Interface Segregation Principle

- The system uses narrow ports instead of one large dependency interface.
- A worker does not need detector methods.
- The API layer does not need tracker internals.

### Dependency Inversion Principle

- High-level services depend on abstract ports.
- Infrastructure implements those ports.
- FastAPI wiring and the container resolve concrete implementations at startup.

### Design consequence

This lets the system remain testable at the unit level and replaceable at the integration level.

## Database Design

The database is intentionally split into raw facts and derived read models.

### Core tables

- events
  - Immutable source of truth for all retail events.
  - Stores event type, timestamps, store and camera identifiers, track/session identifiers, idempotency keys, and payload.

- sessions
  - Represents customer visits and movement sessions.
  - Built from event sequences.

- anomalies
  - Stores derived anomaly records such as queue buildup, abandonment, or unusual dwell patterns.

- metrics_cache
  - Holds precomputed aggregates used by the FastAPI read endpoints.

### Database principles

- Write raw events first.
- Derive sessions and metrics from events.
- Add unique constraints for idempotency.
- Index by store, camera, event type, and time.
- Keep read queries fast by avoiding expensive runtime aggregation.

## Redis Stream Design

Redis Streams should carry canonical event envelopes.

### Recommended fields

- event_id
- idempotency_key
- store_id
- camera_id
- event_type
- track_id
- session_id
- occurred_at
- payload

### Operational rules

- Use consumer groups for worker fan-out.
- Ack messages only after successful database commit.
- Retry transient failures with bounded attempts.
- Send poison messages to a dead-letter stream.
- Keep stream payloads small and structured.

### Why this matters

This design makes the stream a durable buffer, not a second database.

## Component Responsibilities

- API layer
  - Accepts HTTP requests.
  - Validates inputs.
  - Returns read-only responses.

- Application layer
  - Orchestrates use cases.
  - Coordinates repositories and publishers.

- Domain layer
  - Defines events, interfaces, and shared business concepts.

- Infrastructure layer
  - Implements Redis, PostgreSQL, detector, and tracker adapters.

- Worker layer
  - Consumes stream messages.
  - Persists events.
  - Builds aggregates.

## Recommended Implementation Order

1. Finalize domain events and interfaces.
2. Build config, logging, and startup wiring.
3. Add PostgreSQL models and repositories.
4. Add Redis publisher and consumer skeletons.
5. Implement event ingestion and idempotency.
6. Persist raw events and build sessions.
7. Add read models and analytics endpoints.
8. Add integration tests and health checks.
9. Add YOLOv8 and ByteTrack adapters behind the ports.

## Summary

This architecture is intentionally conservative where operational complexity would not improve score, and intentionally modular where extensibility matters. Redis Streams provides asynchronous decoupling, the modular monolith keeps delivery manageable, event-driven design matches the problem domain, and SOLID boundaries preserve long-term maintainability. The result is a production-oriented foundation that can support the challenge without overengineering it.