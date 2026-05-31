# Engineering Design

## System Architecture

The project is a modular monolith with three runtime surfaces:

- CV pipeline runtime for MP4/video processing.
- Worker runtime for Redis Stream consumption and PostgreSQL persistence.
- FastAPI runtime for health and analytics reads.

Each runtime depends on the same domain contracts and infrastructure abstractions.

## Clean Architecture Boundaries

- Domain: event schema, enums, and interfaces.
- Application: use cases and orchestration services.
- Infrastructure: Redis, SQLAlchemy, and external integrations.
- Interface/API: FastAPI routes and request/response DTOs.

Dependencies point inward. Framework details do not leak into domain contracts.

## Event-Driven Design

The system treats events as the primary integration unit.

- CV generates ENTRY and EXIT events.
- API ingests events for structured input.
- Redis Streams buffers event flow.
- Workers materialize events into sessions and analytics tables.

This makes the pipeline resilient to asynchronous load and easier to scale.

## Redis Streams Design

- One durable stream for retail events.
- Consumer groups for worker scalability.
- Ack only after persistence succeeds.
- Pending message claims for retry-safe processing.

Redis is the decoupling layer between real-time event generation and database writes.

## Worker Processing Model

The worker flow is:

1. Read messages from Redis Stream.
2. Validate event payload.
3. Deduplicate via idempotency key.
4. Persist immutable event record.
5. Update session state.
6. Ack only after commit.

Failure leaves the message pending so it can be retried.

## Scalability Strategy

- CV workers scale separately from API workers.
- Redis absorbs bursts.
- PostgreSQL stores facts and derived records.
- Read models can be cached later without changing the contracts.

## Bottlenecks

- YOLO inference latency.
- Video decoding.
- Redis lag under bursty event volume.
- PostgreSQL write throughput.
- Analytics aggregation cost if cache is cold.

## Failure Handling

- Redis publisher retries transient errors.
- Worker logs and retains failed messages for retry.
- Health endpoint reports stale feed detection.
- Structured logs preserve traceability across layers.

## SOLID Principles Usage

- Single responsibility across detector, tracker, publisher, repository, and service classes.
- Open/closed via pluggable implementations.
- Liskov substitution via narrow interfaces.
- Interface segregation through small ports.
- Dependency inversion via container-based wiring.

## Tradeoffs Made

- Chose Redis Streams over Kafka to reduce operational overhead.
- Chose modular monolith over microservices to preserve delivery speed and testability.
- Chose SQL-first analytics over a separate OLAP stack to keep the solution compact.

## Future Evolution Paths

- Add real dashboard UI.
- Add cached materialized views for hot analytics.
- Add per-store pipeline workers.
- Add better claim/retry policies and dead-letter streams.
- Add multi-camera session stitching later if required.
