from __future__ import annotations

import logging
from datetime import datetime

from app.infrastructure.repositories.analytics import AnalyticsRepository

logger = logging.getLogger(__name__)

def attribute_purchases(billing_sessions: list[dict], transactions: list[dict], window_minutes: int = 5) -> tuple[int, set[str]]:
    """
    Deterministic attribution algorithm.
    One transaction -> one session
    One session -> one purchase
    """
    purchase_count = 0
    matched_sessions = set()
    
    # Iterate through transactions, which are already sorted by time ascending from the DB
    for txn in transactions:
        txn_time = txn["timestamp"]
        
        # Find all valid sessions for this transaction
        valid_sessions = []
        for s in billing_sessions:
            if s["session_id"] in matched_sessions:
                continue
                
            billing_time = s["billing_time"]
            
            # Transaction must happen AFTER the billing session starts
            if billing_time <= txn_time:
                # Must be within window
                delta_seconds = (txn_time - billing_time).total_seconds()
                if delta_seconds <= (window_minutes * 60):
                    valid_sessions.append(s)
                    
        if valid_sessions:
            # FIFO attribution: earliest valid session claims the transaction
            best_match = valid_sessions[0]
            matched_sessions.add(best_match["session_id"])
            purchase_count += 1
            
    return purchase_count, matched_sessions

class PurchaseCorrelationService:
    def __init__(self, repository: AnalyticsRepository):
        self._repository = repository

    async def get_funnel_analytics(
        self, 
        store_id: str, 
        start_time: datetime, 
        end_time: datetime, 
        window_minutes: int = 5
    ) -> dict:
        data = await self._repository.get_funnel_data(store_id, start_time, end_time)
        
        entry = data["entry_count"]
        billing_count = len(data["billing_sessions"])
        
        # Execute the deterministic attribution algorithm
        purchase, _ = attribute_purchases(data["billing_sessions"], data["transactions"], window_minutes)
        
        conversion_rate = round(purchase / entry, 4) if entry > 0 else 0.0

        return {
            "entry": entry,
            "zone_visit": data["zone_visit_count"],
            "billing": billing_count,
            "purchase": purchase,
            "conversion_rate": conversion_rate
        }
