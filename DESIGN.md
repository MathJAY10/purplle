# System Design

This document explains the architecture of the Retail Store Analytics Platform. Our main goal was to build a reliable and scalable system that is also easy to understand and maintain.

## Core Architecture: A Modular Approach

We designed the system as a **Modular Monolith**.

*   **What it means:** The entire application runs as a single unit, but the code is organized into independent, self-contained modules. Think of it like a well-organized toolbox, where every tool has its place, instead of a messy drawer where everything is jumbled together.
*   **Why we chose it:**
    *   **Simplicity:** It's much simpler to develop, test, and deploy than a complex microservices architecture, making it ideal for a small team or a new project.
    *   **Performance:** Communication between modules is fast because it happens directly within the application, without slow network calls.
    *   **Maintainability:** The clear boundaries between modules (`api`, `cv`, `workers`) make the code easy to navigate and prevent different parts from becoming tangled.

## How Data Flows Through the System

The system has two main data flows:

1.  **Data Ingestion (Getting data in):** This is how we turn raw video into useful events.
2.  **Data Processing & Serving (Making sense of the data):** This is how we process those events and show them to the user.

Here's a simple breakdown:

### 1. Data Ingestion Flow

`Video File -> CV Pipeline -> Redis (Message Queue)`

1.  **Video File:** The process starts with a video file from a store's camera.
2.  **CV Pipeline:** A dedicated script (`run_pipeline.py`) reads the video frame by frame.
    *   **YOLO (You Only Look Once):** This AI model scans each frame to find and identify people.
    *   **ByteTrack:** This algorithm tracks each person from one frame to the next, assigning them a unique ID so we can follow their journey.
    *   **Event Generation:** When a person's track crosses a pre-defined line (like the store entrance), the system generates an "ENTRY" or "EXIT" event.
3.  **Redis Streams (The "Conveyor Belt"):** Each event is immediately published to a Redis Stream. This acts as a reliable buffer or "conveyor belt," ensuring that events are captured and queued up for processing without getting lost, even if the next part of the system is busy.

### 2. Data Processing & Serving Flow

`Redis -> Worker -> PostgreSQL (Database) -> FastAPI (API)`

1.  **Redis:** The worker process constantly watches the Redis Stream for new events.
2.  **Worker:** This is a background process (`run_worker.py`) that does the heavy lifting.
    *   It picks up new events from the "conveyor belt."
    *   It processes the event data, for example, by creating or updating a customer "session" to calculate visit duration.
    *   It saves the processed data into our main database.
3.  **PostgreSQL (The "Filing Cabinet"):** This is our primary database where all the final, structured data is stored (e.g., event records, traffic metrics, anomaly reports). We chose a traditional SQL database because it's reliable, powerful, and great for running the complex queries needed for analytics.
4.  **FastAPI (The "Storefront"):** This is the web server that exposes our data to the outside world through an API. When a user wants to see the latest analytics on a dashboard, their request comes here. The API queries the PostgreSQL database, formats the data, and sends it back.

## Why Separate the Flows? (Decoupling)

By using Redis as a buffer between ingestion and processing, we **decouple** the two parts of the system.

*   **What it means:** The CV Pipeline (which produces data) and the Worker (which consumes data) don't have to know about each other. They only need to know how to talk to Redis.
*   **Why it's a good idea:**
    *   **Reliability:** If the database or the worker goes down for maintenance, the CV pipeline can keep processing video and publishing events to Redis. Once the worker comes back online, it will catch up on all the queued events. No data is lost.
    *   **Scalability:** If we have a lot of video to process, we can run multiple CV Pipeline instances. If we have a flood of events, we can run multiple Worker instances to process them in parallel. This design makes it easy to scale different parts of the system independently based on the workload.
