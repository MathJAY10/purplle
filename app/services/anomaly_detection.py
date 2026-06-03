import logging
from datetime import datetime, timedelta, timezone

from app.db.models.anomaly import AnomalyRecord
from app.infrastructure.repositories.anomalies import AnomalyRepository
from app.services.purchase_correlation import PurchaseCorrelationService
from app.services.queue_analytics import QueueAnalyticsService

logger = logging.getLogger(__name__)

class AnomalyDetectionService:
    def __init__(
        self, 
        repository: AnomalyRepository,
        correlation_service: PurchaseCorrelationService,
        queue_service: QueueAnalyticsService
    ):
        self._repository = repository
        self._correlation_service = correlation_service
        self._queue_service = queue_service

    async def detect_and_record_anomalies(
        self, 
        store_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> list[AnomalyRecord]:
        
        # Calculate baseline window (T - 7 days)
        baseline_start = start_time - timedelta(days=7)
        baseline_end = end_time - timedelta(days=7)
        
        # Fetch Current Data
        current_funnel = await self._correlation_service.get_funnel_analytics(store_id, start_time, end_time)
        current_queue = await self._queue_service.get_queue_metrics(store_id, start_time, end_time)
        
        # Fetch Baseline Data
        baseline_funnel = await self._correlation_service.get_funnel_analytics(store_id, baseline_start, baseline_end)
        baseline_queue = await self._queue_service.get_queue_metrics(store_id, baseline_start, baseline_end)
        
        anomalies = []
        
        # Rules Engine
        
        # Helper to safely add anomaly if it hasn't been added already
        async def add_anomaly(anomaly_type: str, severity: str, desc: str, metric: float, threshold: float, metadata: dict):
            # Idempotency check
            exists = await self._repository.check_anomaly_exists(store_id, anomaly_type, end_time)
            if not exists:
                anomalies.append(
                    AnomalyRecord(
                        store_id=store_id,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        description=desc,
                        metric_value=metric,
                        threshold_value=threshold,
                        observed_at=end_time,
                        metadata_json=metadata
                    )
                )

        # 1. Traffic Spike / Drop
        curr_entries = current_funnel["entry"]
        base_entries = baseline_funnel["entry"]
        
        if base_entries >= 10:
            ratio = curr_entries / base_entries
            metadata = {"current_entries": curr_entries, "baseline_entries": base_entries, "ratio": ratio}
            
            if ratio > 3.0:
                await add_anomaly("TRAFFIC_SPIKE", "HIGH", "Traffic is > 3x baseline", curr_entries, base_entries * 3.0, metadata)
            elif ratio > 1.5:
                await add_anomaly("TRAFFIC_SPIKE", "LOW", "Traffic is > 1.5x baseline", curr_entries, base_entries * 1.5, metadata)
                
            if ratio < 0.1:
                await add_anomaly("TRAFFIC_DROP", "HIGH", "Traffic is < 0.1x baseline", curr_entries, base_entries * 0.1, metadata)
            elif ratio < 0.5:
                await add_anomaly("TRAFFIC_DROP", "LOW", "Traffic is < 0.5x baseline", curr_entries, base_entries * 0.5, metadata)

        # 2. Queue Spike
        curr_peak = current_queue["peak_queue_size"]
        base_peak = baseline_queue["peak_queue_size"]
        
        # Ensure we have a meaningful baseline queue size to compare against
        if base_peak >= 2:
            ratio = curr_peak / base_peak
            metadata = {"current_peak": curr_peak, "baseline_peak": base_peak, "ratio": ratio}
            
            if ratio > 4.0:
                await add_anomaly("QUEUE_SPIKE", "HIGH", "Peak queue size is > 4x baseline", curr_peak, base_peak * 4.0, metadata)
            elif ratio > 2.0:
                await add_anomaly("QUEUE_SPIKE", "LOW", "Peak queue size is > 2x baseline", curr_peak, base_peak * 2.0, metadata)

        # 3. Conversion Drop
        curr_conv = current_funnel["conversion_rate"]
        base_conv = baseline_funnel["conversion_rate"]
        
        # Only evaluate if baseline had decent traffic
        if base_entries >= 10:
            drop = base_conv - curr_conv
            metadata = {"current_conv": curr_conv, "baseline_conv": base_conv, "absolute_drop": drop}
            
            if drop > 0.30:
                await add_anomaly("CONVERSION_DROP", "HIGH", "Conversion rate dropped > 30% absolute", curr_conv, base_conv - 0.30, metadata)
            elif drop > 0.15:
                await add_anomaly("CONVERSION_DROP", "MEDIUM", "Conversion rate dropped > 15% absolute", curr_conv, base_conv - 0.15, metadata)

        # 4. Dead Zone
        curr_zone_visits = current_funnel["zone_visit"]
        if curr_entries >= 10:
            zone_ratio = curr_zone_visits / curr_entries
            metadata = {"zone_visits": curr_zone_visits, "total_entries": curr_entries, "ratio": zone_ratio}
            
            if zone_ratio == 0.0:
                await add_anomaly("DEAD_ZONE", "HIGH", "Zone traffic is 0 despite store entries", zone_ratio, 0.0, metadata)
            elif zone_ratio < 0.1:
                await add_anomaly("DEAD_ZONE", "LOW", "Zone traffic is < 10% of store entries", zone_ratio, 0.1, metadata)

        # Persist generated anomalies
        if anomalies:
            await self._repository.save_anomalies(anomalies)
            
        return anomalies

    async def get_anomalies(self, store_id: str, start_time: datetime, end_time: datetime):
        return await self._repository.get_anomalies(store_id, start_time, end_time)
