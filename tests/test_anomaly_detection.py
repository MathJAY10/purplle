import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from app.services.anomaly_detection import AnomalyDetectionService
from app.infrastructure.repositories.anomalies import AnomalyRepository
from app.db.models.anomaly import AnomalyRecord

@pytest.mark.asyncio
async def test_anomaly_detection_rules_engine():
    # Setup mocks
    repo_mock = AsyncMock(spec=AnomalyRepository)
    repo_mock.check_anomaly_exists.return_value = False
    
    corr_mock = AsyncMock()
    queue_mock = AsyncMock()
    
    # Baseline Data
    corr_mock.get_funnel_analytics.side_effect = [
        # Call 1: Current window
        {"entry": 50, "zone_visit": 4, "conversion_rate": 0.05},
        # Call 2: Baseline window
        {"entry": 10, "zone_visit": 2, "conversion_rate": 0.40},
    ]
    
    queue_mock.get_queue_metrics.side_effect = [
        # Call 1: Current window
        {"peak_queue_size": 15},
        # Call 2: Baseline window
        {"peak_queue_size": 2},
    ]
    
    service = AnomalyDetectionService(
        repository=repo_mock,
        correlation_service=corr_mock,
        queue_service=queue_mock
    )
    
    now = datetime.now(timezone.utc)
    
    # Run detection
    anomalies = await service.detect_and_record_anomalies("store-test", now - timedelta(hours=1), now)
    
    # Check generated anomalies
    anomaly_types = {a.anomaly_type: a for a in anomalies}
    
    assert "TRAFFIC_SPIKE" in anomaly_types
    assert anomaly_types["TRAFFIC_SPIKE"].severity == "HIGH" # 50 vs 10 (5x > 3x)
    assert anomaly_types["TRAFFIC_SPIKE"].metric_value == 50
    
    assert "QUEUE_SPIKE" in anomaly_types
    assert anomaly_types["QUEUE_SPIKE"].severity == "HIGH" # 15 vs 2 (7.5x > 4x)
    
    assert "CONVERSION_DROP" in anomaly_types
    assert anomaly_types["CONVERSION_DROP"].severity == "HIGH" # 0.40 to 0.05 (drop of 0.35 > 0.30)
    
    assert "DEAD_ZONE" in anomaly_types
    assert anomaly_types["DEAD_ZONE"].severity == "LOW" # 5/50 = 0.1 ratio (<= 0.1)
    
    # Verify save was called
    repo_mock.save_anomalies.assert_called_once()
    
@pytest.mark.asyncio
async def test_anomaly_detection_idempotency():
    repo_mock = AsyncMock(spec=AnomalyRepository)
    # Simulate that anomaly already exists
    repo_mock.check_anomaly_exists.return_value = True
    
    corr_mock = AsyncMock()
    queue_mock = AsyncMock()
    
    # High traffic data
    corr_mock.get_funnel_analytics.return_value = {"entry": 50, "zone_visit": 5, "conversion_rate": 0.05}
    queue_mock.get_queue_metrics.return_value = {"peak_queue_size": 15}
    
    service = AnomalyDetectionService(
        repository=repo_mock,
        correlation_service=corr_mock,
        queue_service=queue_mock
    )
    
    now = datetime.now(timezone.utc)
    anomalies = await service.detect_and_record_anomalies("store-test", now - timedelta(hours=1), now)
    
    # Since it already exists, it should not generate duplicates
    assert len(anomalies) == 0
    repo_mock.save_anomalies.assert_not_called()
