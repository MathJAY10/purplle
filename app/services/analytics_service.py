from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.store_config import StoreConfig
from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import AnomalyResponse, AnomalyResponseItem, FunnelResponse, FunnelStage, HeatmapResponse, HeatmapZoneResponse, MetricsResponse


@dataclass(slots=True)
class MetricsService:
    repository: AnalyticsRepository

    async def get_metrics(self, store_id: str) -> MetricsResponse:
        unique_visitors = await self.repository.unique_visitors(store_id)
        entry_count = await self.repository.entry_count(store_id)
        exit_count = await self.repository.exit_count(store_id)
        avg_dwell_ms = await self.repository.avg_dwell_ms(store_id)
        queue_depth = await self.repository.queue_depth(store_id)
        abandonment_rate = await self.repository.abandonment_rate(store_id)
        conversion_rate = round(exit_count / entry_count, 4) if entry_count else 0.0
        return MetricsResponse(
            unique_visitors=unique_visitors,
            conversion_rate=conversion_rate,
            avg_dwell_time=avg_dwell_ms / 1000.0,
            queue_depth=queue_depth,
            abandonment_rate=abandonment_rate,
        )


@dataclass(slots=True)
class FunnelService:
    repository: AnalyticsRepository

    async def get_funnel(self, store_id: str) -> FunnelResponse:
        entry_count = await self.repository.entry_count(store_id)
        zone_visit_count = sum(item["visits"] for item in await self.repository.zone_metrics(store_id))
        billing_count = await self.repository.queue_depth(store_id)
        purchase_count = await self.repository.exit_count(store_id)

        stages = [
            FunnelStage(stage="ENTRY", count=entry_count, dropoff_percentage=0.0),
            FunnelStage(stage="ZONE_VISIT", count=zone_visit_count, dropoff_percentage=self._dropoff(entry_count, zone_visit_count)),
            FunnelStage(stage="BILLING", count=billing_count, dropoff_percentage=self._dropoff(zone_visit_count, billing_count)),
            FunnelStage(stage="PURCHASE", count=purchase_count, dropoff_percentage=self._dropoff(billing_count, purchase_count)),
        ]
        return FunnelResponse(store_id=store_id, stages=stages)

    def _dropoff(self, previous: int, current: int) -> float:
        if previous <= 0:
            return 0.0
        return round(max(0, previous - current) / previous * 100.0, 2)


@dataclass(slots=True)
class HeatmapService:
    repository: AnalyticsRepository

    async def get_heatmap(self, store_id: str) -> HeatmapResponse:
        zones = await self.repository.zone_metrics(store_id)
        max_visits = max((int(item["visits"]) for item in zones), default=1)
        responses = [
            HeatmapZoneResponse(
                zone=str(item["zone"]),
                visits=int(item["visits"]),
                avg_dwell_ms=float(item["avg_dwell_ms"] or 0.0),
                normalized_score=round(int(item["visits"]) / max_visits, 4),
            )
            for item in zones
        ]
        return HeatmapResponse(store_id=store_id, zones=responses)


@dataclass(slots=True)
class AnomalyService:
    repository: AnalyticsRepository
    store_config: StoreConfig | None = None

    async def get_anomalies(self, store_id: str) -> AnomalyResponse:
        entry_count = await self.repository.entry_count(store_id)
        queue_depth = await self.repository.queue_depth(store_id)
        abandonment_rate = await self.repository.abandonment_rate(store_id)
        zone_metrics = await self.repository.zone_metrics(store_id)

        anomalies: list[AnomalyResponseItem] = []
        if queue_depth >= 10:
            anomalies.append(
                AnomalyResponseItem(
                    anomaly_type="queue_spike",
                    severity="medium",
                    description="Billing queue depth exceeded threshold",
                    metric_value=float(queue_depth),
                    threshold_value=10.0,
                    observed_at=datetime.now(timezone.utc),
                )
            )

        expected_zones = self._expected_zones()
        seen_zones = {str(zone["zone"]) for zone in zone_metrics}
        for zone_name in sorted(expected_zones - seen_zones):
            anomalies.append(
                AnomalyResponseItem(
                    anomaly_type="dead_zone",
                    severity="low",
                    description=f"Zone {zone_name} has no visits",
                    metric_value=0.0,
                    threshold_value=1.0,
                    observed_at=datetime.now(timezone.utc),
                )
            )

        if entry_count >= 10 and abandonment_rate >= 0.5:
            anomalies.append(
                AnomalyResponseItem(
                    anomaly_type="conversion_drop",
                    severity="high",
                    description="Conversion rate dropped below acceptable threshold",
                    metric_value=abandonment_rate,
                    threshold_value=0.5,
                    observed_at=datetime.now(timezone.utc),
                )
            )

        persisted = await self.repository.anomaly_rows(store_id)
        persisted_items = [
            AnomalyResponseItem(
                anomaly_type=item.anomaly_type,
                severity=item.severity,
                description=item.description,
                metric_value=item.metric_value,
                threshold_value=item.threshold_value,
                observed_at=item.observed_at,
            )
            for item in persisted
        ]
        return AnomalyResponse(store_id=store_id, anomalies=persisted_items + anomalies)

    def _expected_zones(self) -> set[str]:
        if self.store_config is None:
            return set()
        zone_names: set[str] = set()
        for camera in self.store_config.cameras:
            zone_names.update(camera.zone_polygons.keys())
        return zone_names


@dataclass(slots=True)
class HealthService:
    repository: AnalyticsRepository
    stale_feed_seconds: int

    async def get_health(self, service_status: str, redis_status: str, db_status: str, store_id: str) -> dict[str, object]:
        last_event_timestamp = await self.repository.last_event_timestamp(store_id)
        now = datetime.now(timezone.utc)
        stale_feed = last_event_timestamp is None or (now - last_event_timestamp).total_seconds() > self.stale_feed_seconds
        return {
            "service_status": service_status,
            "redis_status": redis_status,
            "db_status": db_status,
            "last_event_timestamp": last_event_timestamp,
            "stale_feed": stale_feed,
        }
