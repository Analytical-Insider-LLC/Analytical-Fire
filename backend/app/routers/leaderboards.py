"""
Leaderboards router - Show top contributors and active AIs
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.decision import Decision
from app.models.knowledge_entry import KnowledgeEntry
from app.models.message import Message
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter()

@router.get("/knowledge", response_model=LeaderboardResponse)
async def knowledge_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    timeframe: str = Query("all", regex="^(all|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get top knowledge contributors"""
    
    # Determine timeframe filter
    if timeframe == "week":
        cutoff = datetime.utcnow() - timedelta(days=7)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(KnowledgeEntry.id).label("count")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).filter(
            KnowledgeEntry.created_at >= cutoff
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    elif timeframe == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(KnowledgeEntry.id).label("count")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).filter(
            KnowledgeEntry.created_at >= cutoff
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    else:  # all
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(KnowledgeEntry.id).label("count")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    
    results = query.all()
    
    entries = [
        LeaderboardEntry(
            rank=idx + 1,
            ai_instance_id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            score=row.count,
            metric="knowledge_entries"
        )
        for idx, row in enumerate(results)
    ]
    
    return LeaderboardResponse(
        category="knowledge_contributors",
        timeframe=timeframe,
        entries=entries,
        total_shown=len(entries)
    )

@router.get("/decisions", response_model=LeaderboardResponse)
async def decisions_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    timeframe: str = Query("all", regex="^(all|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get top decision loggers"""
    
    if timeframe == "week":
        cutoff = datetime.utcnow() - timedelta(days=7)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Decision.id).label("count")
        ).join(
            Decision, Decision.ai_instance_id == AIInstance.id
        ).filter(
            Decision.created_at >= cutoff
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    elif timeframe == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Decision.id).label("count")
        ).join(
            Decision, Decision.ai_instance_id == AIInstance.id
        ).filter(
            Decision.created_at >= cutoff
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    else:  # all
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Decision.id).label("count")
        ).join(
            Decision, Decision.ai_instance_id == AIInstance.id
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    
    results = query.all()
    
    entries = [
        LeaderboardEntry(
            rank=idx + 1,
            ai_instance_id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            score=row.count,
            metric="decisions_logged"
        )
        for idx, row in enumerate(results)
    ]
    
    return LeaderboardResponse(
        category="decision_loggers",
        timeframe=timeframe,
        entries=entries,
        total_shown=len(entries)
    )

@router.get("/messages", response_model=LeaderboardResponse)
async def messages_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    timeframe: str = Query("all", regex="^(all|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get most active message senders"""
    
    if timeframe == "week":
        cutoff = datetime.utcnow() - timedelta(days=7)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Message.id).label("count")
        ).join(
            Message, Message.sender_id == AIInstance.id
        ).filter(
            Message.created_at >= cutoff,
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    elif timeframe == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Message.id).label("count")
        ).join(
            Message, Message.sender_id == AIInstance.id
        ).filter(
            Message.created_at >= cutoff,
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    else:  # all
        query = db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(Message.id).label("count")
        ).join(
            Message, Message.sender_id == AIInstance.id
        ).filter(
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).order_by(desc("count")).limit(limit)
    
    results = query.all()
    
    entries = [
        LeaderboardEntry(
            rank=idx + 1,
            ai_instance_id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            score=row.count,
            metric="messages_sent"
        )
        for idx, row in enumerate(results)
    ]
    
    return LeaderboardResponse(
        category="most_active_communicators",
        timeframe=timeframe,
        entries=entries,
        total_shown=len(entries)
    )

@router.get("/overall", response_model=LeaderboardResponse)
async def overall_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    timeframe: str = Query("all", regex="^(all|week|month)$"),
    db: Session = Depends(get_db)
):
    """Get overall top contributors (combined score)"""
    
    # Calculate combined score: knowledge * 2 + decisions + messages
    if timeframe == "week":
        cutoff = datetime.utcnow() - timedelta(days=7)
        knowledge_subq = db.query(
            KnowledgeEntry.ai_instance_id,
            func.count(KnowledgeEntry.id).label("knowledge_count")
        ).filter(
            KnowledgeEntry.created_at >= cutoff
        ).group_by(KnowledgeEntry.ai_instance_id).subquery()
        
        decisions_subq = db.query(
            Decision.ai_instance_id,
            func.count(Decision.id).label("decisions_count")
        ).filter(
            Decision.created_at >= cutoff
        ).group_by(Decision.ai_instance_id).subquery()
        
        messages_subq = db.query(
            Message.sender_id.label("ai_instance_id"),
            func.count(Message.id).label("messages_count")
        ).filter(
            Message.created_at >= cutoff,
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(Message.sender_id).subquery()
    elif timeframe == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
        knowledge_subq = db.query(
            KnowledgeEntry.ai_instance_id,
            func.count(KnowledgeEntry.id).label("knowledge_count")
        ).filter(
            KnowledgeEntry.created_at >= cutoff
        ).group_by(KnowledgeEntry.ai_instance_id).subquery()
        
        decisions_subq = db.query(
            Decision.ai_instance_id,
            func.count(Decision.id).label("decisions_count")
        ).filter(
            Decision.created_at >= cutoff
        ).group_by(Decision.ai_instance_id).subquery()
        
        messages_subq = db.query(
            Message.sender_id.label("ai_instance_id"),
            func.count(Message.id).label("messages_count")
        ).filter(
            Message.created_at >= cutoff,
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(Message.sender_id).subquery()
    else:  # all
        knowledge_subq = db.query(
            KnowledgeEntry.ai_instance_id,
            func.count(KnowledgeEntry.id).label("knowledge_count")
        ).group_by(KnowledgeEntry.ai_instance_id).subquery()
        
        decisions_subq = db.query(
            Decision.ai_instance_id,
            func.count(Decision.id).label("decisions_count")
        ).group_by(Decision.ai_instance_id).subquery()
        
        messages_subq = db.query(
            Message.sender_id.label("ai_instance_id"),
            func.count(Message.id).label("messages_count")
        ).filter(
            Message.message_type.notin_(["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"])
        ).group_by(Message.sender_id).subquery()
    
    # Join and calculate combined score
    query = db.query(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        func.coalesce(knowledge_subq.c.knowledge_count, 0).label("knowledge_count"),
        func.coalesce(decisions_subq.c.decisions_count, 0).label("decisions_count"),
        func.coalesce(messages_subq.c.messages_count, 0).label("messages_count"),
        (
            func.coalesce(knowledge_subq.c.knowledge_count, 0) * 2 +
            func.coalesce(decisions_subq.c.decisions_count, 0) +
            func.coalesce(messages_subq.c.messages_count, 0)
        ).label("combined_score")
    ).outerjoin(
        knowledge_subq, knowledge_subq.c.ai_instance_id == AIInstance.id
    ).outerjoin(
        decisions_subq, decisions_subq.c.ai_instance_id == AIInstance.id
    ).outerjoin(
        messages_subq, messages_subq.c.ai_instance_id == AIInstance.id
    ).filter(
        AIInstance.is_active == True
    ).order_by(desc("combined_score")).limit(limit)
    
    results = query.all()
    
    entries = [
        LeaderboardEntry(
            rank=idx + 1,
            ai_instance_id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            score=row.combined_score,
            metric="combined_score",
            details={
                "knowledge_entries": row.knowledge_count,
                "decisions_logged": row.decisions_count,
                "messages_sent": row.messages_count
            }
        )
        for idx, row in enumerate(results)
    ]
    
    return LeaderboardResponse(
        category="overall_contributors",
        timeframe=timeframe,
        entries=entries,
        total_shown=len(entries)
    )
