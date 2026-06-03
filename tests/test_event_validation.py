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
            "visitor_id": "VIS_abc123",  # Re-ID token
            "confidence": 0.93,  # Detection confidence (now required)
            "is_staff": False,  # Staff flag
            "payload": {"confidence": 0.93},
        }
    )

    assert item.store_id == "store-1"
    assert item.event_type == EventType.ENTRY
    assert item.visitor_id == "VIS_abc123"
    assert item.confidence == 0.93
    assert item.is_staff is False


def test_retail_event_ingest_item_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RetailEventIngestItem.model_validate(
            {
                "store_id": "store-1",
                "camera_id": "camera-entry",
                "event_type": EventType.ENTRY,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.85,
                "payload": {},
                "unexpected": True,
            }
        )
