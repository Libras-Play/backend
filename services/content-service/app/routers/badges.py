"""
FASE 5: Badges Router (Content Service)

Endpoints for badge master data.

ANTI-ERROR DESIGN:
- Simple queries, filter in memory if needed
- NO array operations in SQL
- NO ENUMS
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.db import get_db
from app.models import BadgeMaster
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/badges", tags=["badges"])


@router.get("/", response_model=List[dict])
async def get_badges(
    learning_language: Optional[str] = Query(None, description="LSB, ASL, LSM"),
    badge_type: Optional[str] = Query(None, description="milestone, achievement, etc"),
    rarity: Optional[str] = Query(None, description="common, rare, epic, legendary"),
    db: Session = Depends(get_db)
):
    """
    Get all badge definitions.
    
    ANTI-ERROR: Filter in memory, NOT in SQL to avoid complex queries
    """
    try:
        # Fetch all badges
        query = db.query(BadgeMaster)
        
        # Simple filters (no array operations)
        if learning_language:
            query = query.filter(BadgeMaster.learning_language == learning_language)
        
        if badge_type:
            query = query.filter(BadgeMaster.type == badge_type)
        
        if rarity:
            query = query.filter(BadgeMaster.rarity == rarity)
        
        badges = query.order_by(BadgeMaster.order_index).all()
        
        # Convert to dict
        result = []
        for badge in badges:
            result.append({
                'badge_id': badge.badge_id,
                'type': badge.type,
                'title': badge.title,
                'description': badge.description,
                'icon_url': badge.icon_url,
                'conditions': badge.conditions,
                'learning_language': badge.learning_language,
                'is_hidden': badge.is_hidden,
                'rarity': badge.rarity,
                'order_index': badge.order_index,
                'created_at': badge.created_at.isoformat() if badge.created_at else None,
                'updated_at': badge.updated_at.isoformat() if badge.updated_at else None
            })
        
        logger.info(f"Retrieved {len(result)} badges")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching badges: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{badge_id}")
async def get_badge(
    badge_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific badge by ID"""
    try:
        badge = db.query(BadgeMaster).filter(BadgeMaster.badge_id == badge_id).first()
        
        if not badge:
            raise HTTPException(status_code=404, detail="Badge not found")
        
        return {
            'badge_id': badge.badge_id,
            'type': badge.type,
            'title': badge.title,
            'description': badge.description,
            'icon_url': badge.icon_url,
            'conditions': badge.conditions,
            'learning_language': badge.learning_language,
            'is_hidden': badge.is_hidden,
            'rarity': badge.rarity,
            'order_index': badge.order_index,
            'created_at': badge.created_at.isoformat() if badge.created_at else None,
            'updated_at': badge.updated_at.isoformat() if badge.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching badge {badge_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_badge(
    badge_data: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new badge.
    
    Body example:
    {
        "type": "milestone",
        "title": {"es": "...", "en": "...", "pt": "..."},
        "description": {"es": "...", "en": "...", "pt": "..."},
        "icon_url": "https://...",
        "conditions": {"metric": "xp", "operator": ">=", "value": 1000},
        "learning_language": "LSB",
        "rarity": "common"
    }
    """
    try:
        # Generate ID if not provided
        badge_id = badge_data.get('badge_id') or str(uuid.uuid4())
        
        new_badge = BadgeMaster(
            badge_id=badge_id,
            type=badge_data['type'],
            title=badge_data['title'],
            description=badge_data['description'],
            icon_url=badge_data['icon_url'],
            conditions=badge_data['conditions'],
            learning_language=badge_data['learning_language'],
            is_hidden=badge_data.get('is_hidden', False),
            rarity=badge_data.get('rarity', 'common'),
            order_index=badge_data.get('order_index', 0)
        )
        
        db.add(new_badge)
        db.commit()
        db.refresh(new_badge)
        
        logger.info(f"Created badge: {badge_id}")
        
        return {
            'badge_id': new_badge.badge_id,
            'message': 'Badge created successfully'
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating badge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
