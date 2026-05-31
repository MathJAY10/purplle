from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class CameraConfig:
    camera_id: str
    source: str
    entry_line: list[dict[str, float]]
    zone_polygons: dict[str, list[list[float]]]
    thresholds: dict[str, float]
    frame_skip: int = 2


@dataclass(frozen=True, slots=True)
class StoreConfig:
    store_id: str
    name: str
    timezone: str
    cameras: list[CameraConfig]


class StoreConfigLoader:
    def __init__(self, config_dir: str | Path) -> None:
        self._config_dir = Path(config_dir)

    def load(self, store_id: str) -> StoreConfig:
        config_path = self._config_dir / f"{store_id}.yaml"
        if not config_path.exists():
            config_path = self._config_dir / "default.yaml"
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return self._parse_store_config(raw)

    def _parse_store_config(self, raw: dict[str, Any]) -> StoreConfig:
        cameras = [
            CameraConfig(
                camera_id=item["camera_id"],
                source=item["source"],
                entry_line=item.get("entry_line", []),
                zone_polygons=item.get("zone_polygons", {}),
                thresholds=item.get("thresholds", {}),
                frame_skip=int(item.get("frame_skip", 2)),
            )
            for item in raw.get("cameras", [])
        ]
        return StoreConfig(
            store_id=raw.get("store_id", "default-store"),
            name=raw.get("name", "Default Store"),
            timezone=raw.get("timezone", "UTC"),
            cameras=cameras,
        )
