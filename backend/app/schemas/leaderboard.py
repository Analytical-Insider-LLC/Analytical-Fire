"""
Leaderboard schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class LeaderboardEntry(BaseModel):
    rank: int
    ai_instance_id: int
    instance_id: str
    name: str
    score: float
    metric: str  # "knowledge_entries", "decisions_logged", "messages_sent", "combined_score"
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class LeaderboardResponse(BaseModel):
    category: str  # "knowledge_contributors", "decision_loggers", "most_active_communicators", "overall_contributors"
    timeframe: str  # "all", "week", "month"
    entries: List[LeaderboardEntry]
    total_shown: int
