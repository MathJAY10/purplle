from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.events import EventType
from app.schemas.events import RetailEventIngestItem


def test_retail_event_ingest_item_validates() -> None:
    item = RetailEventIngestItem.model_validate(
        {
            "store_id": "store-1",
            "camera_id": "camera-entry",
            "event_type": EventType.ENTRY,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "track_id": "track-1",
            "payload": {"confidence": 0.93},
        }
    )

    assert item.store_id == "store-1"
    assert item.event_type == EventType.ENTRY


def test_retail_event_ingest_item_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RetailEventIngestItem.model_validate(
            {
                "store_id": "store-1",
                "camera_id": "camera-entry",
                "event_type": EventType.ENTRY,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "payload": {},
                "unexpected": True,
            }
        )
