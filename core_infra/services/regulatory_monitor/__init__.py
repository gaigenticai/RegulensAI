"""
Regulatory monitoring service stubs
"""
from typing import Dict, Any

class RegulatoryMonitor:
    """Stub regulatory monitor"""
    pass

class RegulatoryScheduler:
    """Stub regulatory scheduler"""  
    pass

# Module-level instances
regulatory_monitor = RegulatoryMonitor()
regulatory_scheduler = RegulatoryScheduler()

def get_monitor_status() -> Dict[str, Any]:
    """Get monitor status"""
    return {"status": "active", "sources": 0}

def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status"""
    return {"status": "active", "scheduled_tasks": 0} 