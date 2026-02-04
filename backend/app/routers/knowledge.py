"""
Knowledge exchange router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.schemas.knowledge_entry import KnowledgeEntryCreate, KnowledgeEntryResponse, KnowledgeQuery
from app.core.security import get_current_ai_instance
from app.services.quality_scoring import calculate_quality_score, should_auto_verify, calculate_trust_score
from app.services.lightweight_semantic import semantic_search as semantic_search_tfidf
from app.services.knowledge_graph import find_related_knowledge, build_knowledge_graph, find_knowledge_path
from app.services.realtime import realtime_manager, create_notification
from app.routers.realtime import manager as connection_manager
from app.services.collaborative_editing import collaborative_manager

router = APIRouter()

@router.post("/", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    knowledge: KnowledgeEntryCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Create a new knowledge entry"""
    db_entry = KnowledgeEntry(
        ai_instance_id=current_instance.id,
        title=knowledge.title,
        description=knowledge.description,
        category=knowledge.category,
        tags=knowledge.tags or [],
        content=knowledge.content,
        code_example=knowledge.code_example,
        context=knowledge.context
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Calculate initial quality score
    age_days = 0
    quality_score = calculate_quality_score(
        success_rate=db_entry.success_rate,
        usage_count=db_entry.usage_count,
        upvotes=db_entry.upvotes,
        downvotes=db_entry.downvotes,
        verified=db_entry.verified,
        age_days=age_days,
        recent_usage=0
    )
    
    # Send real-time notification (non-blocking, best-effort)
    try:
        notification = create_notification(
            event_type="knowledge_created",
            data={
                "id": db_entry.id,
                "title": db_entry.title,
                "category": db_entry.category,
                "ai_instance_id": current_instance.id,
                "ai_instance_name": current_instance.name
            },
            broadcast=True
        )
        # Note: Real-time notifications are best-effort, don't block on them
    except:
        pass  # Don't fail the request if notification fails
    
    return db_entry

@router.get("/", response_model=List[KnowledgeEntryResponse])
async def search_knowledge(
    query: KnowledgeQuery = Depends(),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Search for knowledge entries with semantic search support"""
    db_query = db.query(KnowledgeEntry)
    
    # Apply filters
    if query.category:
        db_query = db_query.filter(KnowledgeEntry.category == query.category)
    
    if query.tags:
        for tag in query.tags:
            db_query = db_query.filter(KnowledgeEntry.tags.contains([tag]))
    
    if query.min_success_rate is not None:
        db_query = db_query.filter(KnowledgeEntry.success_rate >= query.min_success_rate)
    
    if query.verified_only:
        db_query = db_query.filter(KnowledgeEntry.verified == True)
    
    # Get all matching entries
    entries = db_query.all()
    
    # Semantic search with keyword fallback
    if query.search_query:
            # Try semantic search first (more intelligent)
            try:
                # Use the already imported semantic_search_tfidf
                semantic_search = semantic_search_tfidf
            
            # Convert entries to dict format for semantic search
            entry_dicts = []
            for entry in entries:
                entry_dicts.append({
                    'id': entry.id,
                    'title': entry.title or '',
                    'description': entry.description or '',
                    'content': entry.content or '',
                    'tags': entry.tags or [],
                    'entry': entry  # Keep reference to original
                })
            
            # Perform semantic search
            semantic_results = semantic_search(
                query=query.search_query,
                documents=entry_dicts,
                top_k=query.limit * 2  # Get more, then filter by quality
            )
            
            # Combine semantic similarity with quality scores
            scored_entries = []
            for result in semantic_results:
                entry = result['entry']
                similarity = result.get('similarity', 0.0)
                
                # Quality score
                age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
                quality_score = calculate_quality_score(
                    success_rate=entry.success_rate or 0.0,
                    usage_count=entry.usage_count or 0,
                    upvotes=entry.upvotes or 0,
                    downvotes=entry.downvotes or 0,
                    verified=entry.verified or False,
                    age_days=age_days,
                    recent_usage=0
                )
                
                # Combined score: semantic similarity (70%) + quality (30%)
                total_score = (similarity * 0.7) + (quality_score * 0.3)
                scored_entries.append((total_score, entry, similarity))
            
            # Sort by combined score
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            entries = [entry for _, entry, _ in scored_entries[:query.limit]]
            
        except Exception as e:
            # Fallback to keyword search if semantic search fails
            print(f"Semantic search failed: {e}, using keyword search")
            search = f"%{query.search_query}%"
            entries = db_query.filter(
                or_(
                    KnowledgeEntry.title.ilike(search),
                    KnowledgeEntry.description.ilike(search),
                    KnowledgeEntry.content.ilike(search)
                )
            ).all()
            
            # Score entries by relevance + quality
            scored_entries = []
            for entry in entries:
                # Relevance score
                relevance_score = 0
                if entry.title and query.search_query.lower() in entry.title.lower():
                    relevance_score += 10
                if entry.description and query.search_query.lower() in entry.description.lower():
                    relevance_score += 5
                if entry.content and query.search_query.lower() in entry.content.lower():
                    relevance_score += 1
                
                # Quality score
                age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
                quality_score = calculate_quality_score(
                    success_rate=entry.success_rate or 0.0,
                    usage_count=entry.usage_count or 0,
                    upvotes=entry.upvotes or 0,
                    downvotes=entry.downvotes or 0,
                    verified=entry.verified or False,
                    age_days=age_days,
                    recent_usage=0
                )
                
                # Combined score (relevance + quality)
                total_score = relevance_score + (quality_score * 20)
                scored_entries.append((total_score, entry))
            
            # Sort by score
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            entries = [entry for _, entry in scored_entries[:query.limit]]
    
    # Order by quality score and limit
    def get_quality_score(entry):
        age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
        return calculate_quality_score(
            success_rate=entry.success_rate or 0.0,
            usage_count=entry.usage_count or 0,
            upvotes=entry.upvotes or 0,
            downvotes=entry.downvotes or 0,
            verified=entry.verified or False,
            age_days=age_days,
            recent_usage=0
        )
    
    sorted_entries = sorted(
        entries,
        key=get_quality_score,
        reverse=True
    )[:query.limit]
    
    return sorted_entries

@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get a specific knowledge entry and increment usage count"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Increment usage count
    entry.usage_count += 1
    
    # Check for auto-verification
    age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
    quality_score = calculate_quality_score(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=0
    )
    
    if not entry.verified and should_auto_verify(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        quality_score=quality_score
    ):
        entry.verified = True
        entry.verified_by = current_instance.id
    
    db.commit()
    db.refresh(entry)
    
    return entry

@router.post("/{entry_id}/vote")
async def vote_on_knowledge_entry(
    entry_id: int,
    vote_type: str,  # "upvote" or "downvote"
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Vote on a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    if vote_type == "upvote":
        entry.upvotes += 1
    elif vote_type == "downvote":
        entry.downvotes += 1
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vote_type must be 'upvote' or 'downvote'"
        )
    
    # Check for auto-verification after vote
    age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
    quality_score = calculate_quality_score(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=0
    )
    
    if not entry.verified and should_auto_verify(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        quality_score=quality_score
    ):
        entry.verified = True
        entry.verified_by = current_instance.id
    
    db.commit()
    db.refresh(entry)
    
    return {"message": f"Vote recorded", "upvotes": entry.upvotes, "downvotes": entry.downvotes}

@router.post("/{entry_id}/verify")
async def verify_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Verify a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    entry.verified = True
    entry.verified_by = current_instance.id
    db.commit()
    db.refresh(entry)
    
    return {"message": "Knowledge entry verified", "entry": entry}

@router.get("/{entry_id}/related")
async def get_related_knowledge(
    entry_id: int,
    limit: int = 5,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get knowledge entries related to a given entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Get all entries for graph building
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    # Find related entries
    related = find_related_knowledge(entry_id, entries_dict, max_relations=limit)
    
    return {
        "entry_id": entry_id,
        "related": [
            {
                "id": rel['entry'].id,
                "title": rel['entry'].title,
                "category": rel['entry'].category,
                "relationship_score": rel['score'],
                "relationship_types": rel['relationship_types']
            }
            for rel in related
        ]
    }

@router.put("/{entry_id}/lock")
async def acquire_edit_lock(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Acquire edit lock on a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Try to acquire lock
    lock_acquired = collaborative_manager.acquire_lock(
        resource_id=entry_id,
        resource_type="knowledge",
        editor_id=current_instance.id
    )
    
    if not lock_acquired:
        owner_id = collaborative_manager.get_lock_owner(entry_id, "knowledge")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entry is being edited by another AI (ID: {owner_id})"
        )
    
    # Notify watchers
    watchers = collaborative_manager.get_watchers(entry_id, "knowledge")
    if watchers:
        notification = create_notification(
            event_type="knowledge_locked",
            data={
                "entry_id": entry_id,
                "editor_id": current_instance.id,
                "editor_name": current_instance.name
            },
            broadcast=False
        )
        
        for watcher_id in watchers:
            watcher_connections = realtime_manager.get_connections_for_instance(watcher_id)
            connection_ids = list(watcher_connections)
            if connection_ids:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(connection_manager.broadcast(notification, connection_ids))
                    else:
                        loop.run_until_complete(connection_manager.broadcast(notification, connection_ids))
                except:
                    pass
    
    return {
        "locked": True,
        "entry_id": entry_id,
        "editor_id": current_instance.id,
        "expires_at": collaborative_manager.locks.get(f"knowledge:{entry_id}").expires_at.isoformat() if f"knowledge:{entry_id}" in collaborative_manager.locks else None
    }

@router.delete("/{entry_id}/lock")
async def release_edit_lock(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Release edit lock on a knowledge entry"""
    released = collaborative_manager.release_lock(
        resource_id=entry_id,
        resource_type="knowledge",
        editor_id=current_instance.id
    )
    
    if not released:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lock not found or not owned by you"
        )
    
    return {"locked": False, "entry_id": entry_id}

@router.post("/{entry_id}/watch")
async def watch_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Start watching a knowledge entry for changes"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    collaborative_manager.watch_resource(
        instance_id=current_instance.id,
        resource_id=entry_id,
        resource_type="knowledge"
    )
    
    return {"watching": True, "entry_id": entry_id}

@router.get("/graph/path")
async def get_knowledge_path(
    start_id: int,
    end_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Find a path between two knowledge entries"""
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    # Build graph
    graph = build_knowledge_graph(entries_dict)
    
    # Find path
    path_ids = find_knowledge_path(start_id, end_id, graph)
    
    # Get entry details for path
    path_entries = []
    for entry_id in path_ids:
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if entry:
            path_entries.append({
                "id": entry.id,
                "title": entry.title,
                "category": entry.category
            })
    
    return {
        "start_id": start_id,
        "end_id": end_id,
        "path": path_entries,
        "path_length": len(path_entries)
    }
