# Design Choices

## YOLOv8n

### Options considered

- YOLOv8n
- Larger YOLO variants
- Other detectors

### Pros

- Lightweight and fast.
- Good baseline accuracy for person detection.
- Easier to run locally and in Docker.

### Cons

- Lower accuracy than larger models.
- Can miss small or occluded people in difficult footage.

### Final reasoning

YOLOv8n is the best tradeoff for a challenge that values production readiness and demo speed over maximum detection accuracy.

### Operational tradeoff

Slightly lower accuracy is acceptable because the architecture allows model replacement later without changing the pipeline.

## ByteTrack

### Options considered

- ByteTrack
- DeepSORT
- Custom tracking logic

### Pros

- Stable track IDs with minimal overhead.
- Strong fit for detection-to-tracking pipelines.
- No re-identification complexity required.

### Cons

- Not ideal for long-term identity across cameras.

### Final reasoning

ByteTrack is enough for stable in-store trajectories and event generation.

### Operational tradeoff

The system avoids the complexity of re-identification and cross-camera stitching until it is truly needed.

## Redis Streams Instead of Kafka

### Options considered

- Redis Streams
- Kafka

### Pros of Redis Streams

- Simpler local and Docker operations.
- Enough for challenge-scale buffering and consumer groups.
- Lower configuration and maintenance burden.

### Cons

- Less ecosystem maturity than Kafka.
- Fewer advanced streaming features.

### Final reasoning

Redis Streams is the correct complexity level for this project.

### Operational tradeoff

The solution stays easy to run and demo while preserving a real event-driven architecture.

## Modular Monolith Instead of Microservices

### Options considered

- Modular monolith
- Microservices

### Pros of modular monolith

- Easier to test.
- Easier to deploy.
- Easier to reason about.
- Shared domain contracts stay consistent.

### Cons

- Requires discipline to keep boundaries clean.

### Final reasoning

The workload is cohesive enough that service boundaries would add more cost than value.

### Operational tradeoff

The codebase must remain modular and disciplined, but operational complexity stays low.

## Event-Driven Architecture

### Options considered

- Event-driven pipeline
- Direct synchronous writes from CV to DB

### Pros

- Decouples producer and consumer.
- Improves throughput.
- Buffers bursts.
- Supports retries and eventual consistency.

### Cons

- More moving parts than direct writes.

### Final reasoning

This is the natural model for movement-derived retail intelligence.

### Operational tradeoff

The system accepts eventual consistency in exchange for resilience and scale.

## Immutable Events

### Options considered

- Immutable append-only events
- Mutable operational rows

### Pros

- Better auditability.
- Easier replay and debugging.
- Safer analytics derivation.

### Cons

- Requires derived read models for convenience.

### Final reasoning

Retail intelligence is easier to trust when the source facts are immutable.

## PostgreSQL

### Options considered

- PostgreSQL
- SQLite
- NoSQL store

### Pros

- Strong transactional guarantees.
- Good indexing and aggregation support.
- Great fit for sessions and event facts.

### Cons

- Less elastic than specialized analytics engines at large scale.

### Final reasoning

PostgreSQL is the correct source of truth for this project.

## Intentionally Not Implemented

- Re-identification
- Multi-camera identity stitching
- Dashboard UI beyond documentation placeholders
- Heatmap visualization front end
- Advanced anomaly ML models
- Kafka
- Microservices

### Why

These would increase complexity without improving the core challenge score at this stage. The project focuses on correctness, maintainability, and production readiness.
