from datetime import datetime
import statistics

from app.infrastructure.repositories.analytics import AnalyticsRepository
from app.services.purchase_correlation import attribute_purchases

class QueueAnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self._repository = repository

    async def get_queue_metrics(
        self, 
        store_id: str, 
        start_time: datetime, 
        end_time: datetime, 
        window_minutes: int = 5
    ) -> dict:
        # 1. Get queue ledger data
        ledger_data = await self._repository.get_queue_ledger_data(store_id, start_time, end_time)
        baseline_sessions = set(ledger_data["baseline_sessions"])
        ledger_events = ledger_data["ledger_events"]
        
        # We also need funnel data for abandonment computation
        funnel_data = await self._repository.get_funnel_data(store_id, start_time, end_time)
        purchase_count, matched_sessions = attribute_purchases(
            funnel_data["billing_sessions"], 
            funnel_data["transactions"], 
            window_minutes
        )
        
        queue_entries = 0
        queue_exits = 0
        current_queue_size = len(baseline_sessions)
        peak_queue_size = current_queue_size
        
        # Sort events: primary by time ascending, secondary by type (EXIT before ENTER for ties)
        def sort_key(event):
            # ZONE_EXIT (-1) before ZONE_ENTER (+1)
            type_weight = 0 if event["event_type"] == "ZONE_EXIT" else 1
            return (event["occurred_at"], type_weight)
            
        ledger_events.sort(key=sort_key)
        
        session_enters = {}
        session_exits = {}
        wait_times_sec = []
        abandonment_count = 0
        
        for event in ledger_events:
            sid = event["session_id"]
            if event["event_type"] == "ZONE_ENTER":
                queue_entries += 1
                current_queue_size += 1
                if current_queue_size > peak_queue_size:
                    peak_queue_size = current_queue_size
                    
                if sid not in session_enters:
                    session_enters[sid] = event["occurred_at"]
                    
            elif event["event_type"] == "ZONE_EXIT":
                queue_exits += 1
                current_queue_size -= 1
                
                # Check for abandonment: they exited but no purchase
                if sid not in matched_sessions:
                    abandonment_count += 1
                    
                # Track latest exit for wait time
                session_exits[sid] = event["occurred_at"]

        # Calculate wait times: from first enter to last exit
        for sid, enter_time in session_enters.items():
            if sid in session_exits:
                exit_time = session_exits[sid]
                # In case they entered before window but exited in window, we might not have enter_time
                if exit_time >= enter_time:
                    wait_times_sec.append((exit_time - enter_time).total_seconds())
                    
        # Include baseline sessions that exited in the window
        for sid, exit_time in session_exits.items():
            if sid not in session_enters and sid in baseline_sessions:
                # We don't have their true enter time! This is a limitation.
                pass
                
        # Calculate stats
        avg_wait = sum(wait_times_sec) / len(wait_times_sec) if wait_times_sec else 0.0
        median_wait = statistics.median(wait_times_sec) if wait_times_sec else 0.0
        
        # Abandonment Rate
        total_resolved = purchase_count + abandonment_count
        abandonment_rate = round(abandonment_count / total_resolved, 4) if total_resolved > 0 else 0.0
        
        return {
            "queue_entries": queue_entries,
            "queue_exits": queue_exits,
            "avg_wait_time_seconds": round(avg_wait, 2),
            "median_wait_time_seconds": round(median_wait, 2),
            "abandonment_count": abandonment_count,
            "abandonment_rate": abandonment_rate,
            "current_queue_size": current_queue_size,
            "peak_queue_size": peak_queue_size
        }
