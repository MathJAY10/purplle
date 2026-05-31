from __future__ import annotations

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import get_event_ingest_service
from app.schemas.events import EventIngestRequest, EventIngestResponse
from app.services.event_ingest_service import RetailEventIngestService

router = APIRouter(prefix="/events")
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=EventIngestResponse)
async def ingest_events(
    request: Request,
    payload: EventIngestRequest,
    service: RetailEventIngestService = Depends(get_event_ingest_service),
) -> EventIngestResponse:
    started_at = perf_counter()
    published_event_ids, duplicate_event_ids = await service.ingest(payload.events, trace_id=request.state.trace_id)
    latency_ms = round((perf_counter() - started_at) * 1000, 2)

    logger.info(
        "batch_events_ingested",
        extra={
            "trace_id": request.state.trace_id,
            "event_id": str(published_event_ids[0]) if published_event_ids else None,
            "store_id": payload.events[0].store_id if payload.events else None,
            "latency_ms": latency_ms,
        },
    )

    return EventIngestResponse(
        accepted=len(published_event_ids),
        event_ids=published_event_ids,
        duplicate_event_ids=duplicate_event_ids,
    )
