# Technology Choices

## FastAPI

Chosen for:

* High performance
* Async support
* Automatic OpenAPI documentation
* Excellent developer experience

Alternative considered:

* Django REST Framework

FastAPI provided lower overhead and better support for asynchronous workloads.

---

## PostgreSQL

Chosen for:

* Reliability
* Strong consistency
* Rich SQL capabilities
* Mature ecosystem

The analytics layer relies heavily on aggregations and time-series style queries, making PostgreSQL a strong fit.

---

## Redis Streams

Chosen for:

* Event buffering
* Consumer groups
* Low latency
* Operational simplicity

Alternative considered:

* RabbitMQ
* Kafka

Redis Streams provided the right balance between functionality and deployment complexity.

---

## YOLOv8

Chosen for:

* High detection accuracy
* Real-time inference capability
* Large community adoption

Used for person detection across CCTV frames.

---

## ByteTrack

Chosen for:

* Strong tracking performance
* Stability under occlusion
* Efficient real-time execution

Used to maintain identities across video frames.

---

## Docker

Chosen for:

* Environment consistency
* Easy deployment
* Simplified onboarding

All major services run through Docker Compose.
