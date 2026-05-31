# Technology Choices

This document explains the "why" behind the key technologies used in this project. Our goal was to choose modern, high-performance tools that are also widely used and easy to work with.

---

### Backend Framework: FastAPI

*   **What it is:** A modern, high-performance web framework for building APIs with Python.
*   **Why we chose it:**
    *   **Speed:** It's one of the fastest Python frameworks available, which is important for a responsive analytics dashboard.
    *   **Ease of Use:** It uses standard Python type hints to define API endpoints, which makes the code clean, easy to read, and less error-prone.
    *   **Automatic Docs:** It automatically generates interactive API documentation (like Swagger UI), which is incredibly helpful for development and testing.
*   **Alternative Considered:** Django Rest Framework. We chose FastAPI because it's lighter, faster, and its modern async capabilities were a better fit for this project.

---

### Message Queue: Redis Streams

*   **What it is:** A feature of the Redis in-memory database that provides a persistent, log-like message queue.
*   **Why we chose it:**
    *   **Decoupling:** It acts as a buffer between the CV pipeline (producing data) and the worker (processing data). This makes the system more resilient; if the worker is slow or offline, data from the cameras isn't lost.
    *   **Performance:** Redis is extremely fast, which is perfect for handling a high volume of real-time events from many cameras.
    *   **Simplicity:** It's simpler to set up and manage than larger, more complex message brokers like RabbitMQ or Kafka, making it a good fit for this project's scale.
*   **Alternative Considered:** RabbitMQ. We chose Redis Streams for its simplicity and because we were already planning to use Redis for other caching purposes (a common use case).

---

### Database: PostgreSQL

*   **What it is:** A powerful, open-source relational database (SQL).
*   **Why we chose it:**
    *   **Reliability & Power:** It's known for being extremely reliable and feature-rich. It can handle the complex queries needed for our analytics (e.g., calculating funnels, time-based metrics, and anomalies).
    *   **Structured Data:** A traditional SQL database was the right choice because our data has a clear, predictable structure (events, sessions, metrics).
    *   **Maturity:** It's a mature technology with a huge community and excellent documentation.
*   **Alternative Considered:** NoSQL databases like MongoDB. We chose PostgreSQL because our data relationships and query patterns were better suited to a structured SQL model.

---

### Computer Vision: YOLOv8 & Custom Tracking

*   **What they are:**
    *   **YOLOv8:** A state-of-the-art, real-time object detection model. We use it to find people in each frame of the video.
    *   **ByteTrack (Concept):** Our custom tracking logic is based on the principles of ByteTrack, an efficient algorithm for tracking objects (in our case, people) from one frame to the next.
*   **Why we chose them:**
    *   **Performance:** YOLO is famous for its balance of speed and accuracy, making it possible to process video streams in near real-time.
    *   **Accuracy:** It provides reliable detections, which is crucial for accurate counting and tracking.
    *   **Practicality:** By combining a powerful detector (YOLO) with an efficient tracker (ByteTrack principles), we built a pipeline that is both accurate and computationally efficient.

---

### Background Jobs: Dedicated Python Workers

*   **What it is:** A separate Python process that runs in the background to consume events from Redis and save them to the database.
*   **Why we chose it:**
    *   **Separation of Concerns:** This approach separates the immediate task of serving API requests (done by FastAPI) from the longer-running task of processing event data. This ensures the API remains fast and responsive, even when there's a large backlog of events to process.
    *   **Scalability:** If the number of events increases, we can simply run more worker processes to handle the load, without affecting the API server.
*   **Alternative Considered:** Celery. We chose a simple, custom Python worker for this project because our background tasks are straightforward (read from Redis, write to DB), and we didn't need the complexity and overhead of a large framework like Celery.
