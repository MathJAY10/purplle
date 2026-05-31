# Testing & Validation

This document outlines our approach to ensuring the project is reliable and works as expected. Instead of just planning, we focused on writing actual, automated tests.

## Our Testing Strategy: Pragmatic and Focused

Our philosophy is to write tests that give us the most confidence for the least effort. We focused on two main types of tests:

1.  **Unit Tests:** These are small, fast tests that check a single piece of logic, like a function or a class, in isolation.
2.  **Integration Tests:** These are larger tests that check how different parts of the system work together.

All tests are written using **Pytest**, a popular and easy-to-use Python testing framework.

## What We Tested

Here are some examples of the key scenarios covered by our automated tests:

#### 1. Core CV Logic (`test_line_crossing.py`)

*   **Goal:** Ensure we correctly generate "ENTRY" and "EXIT" events.
*   **How it's tested:** We created a simulated scenario where a tracked object moves across a pre-defined line. The test verifies that:
    *   An `ENTRY` event is generated when the object crosses the line in one direction.
    *   An `EXIT` event is generated when it crosses back.
    *   No duplicate events are created if the object hovers near the line.

#### 2. Database Persistence (`test_db_persistence.py`)

*   **Goal:** Make sure that when we process an event, the data is saved correctly in the database.
*   **How it's tested:** The test simulates an `ENTRY` event for a new customer. It then checks the database to confirm that:
    *   A new `SessionRecord` is created with the correct start time.
    *   An `EventRecord` is created and linked to that session.

#### 3. Idempotency (`test_idempotency.py`)

*   **Goal:** Prevent duplicate data if the same event is accidentally processed twice.
*   **What it means (in simple terms):** No matter how many times we process the same event, the result in the database should be the same as if we processed it only once.
*   **How it's tested:** We run the event processing service twice with the exact same event data. The test then verifies that only **one** set of records (one session, one event) is created in the database. This is crucial for data integrity.

#### 4. Analytics Calculations (`test_metrics.py`, `test_anomalies.py`)

*   **Goal:** Verify that our analytics calculations are correct.
*   **How it's tested:** We populate the database with a specific set of test data (e.g., 10 entries and 5 exits over a specific hour). We then run our analytics services (`MetricsService`, `FunnelService`, etc.) and assert that they return the expected results (e.g., `total_visits` is 10, `current_occupancy` is 5).

## How to Run the Tests

You can run the entire test suite using Docker Compose. This ensures the tests run in a clean, consistent environment with a dedicated test database.

```bash
docker-compose run --rm api pytest
```

This command will start a temporary container, run all the tests, and show the results. Our goal is to always maintain a 100% pass rate.

## Validation Results

The system was validated using automated tests.

Results:
- 16 automated tests passing
- Event validation verified
- Redis publish/consume flow verified
- Database persistence verified
- Idempotency verified
- Analytics calculations verified
- API endpoint validation verified

The goal of these tests is to ensure that customer events are generated, processed, stored, and served correctly through the complete pipeline.