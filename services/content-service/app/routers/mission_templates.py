"""
Mission Templates API - FASE 4
Gestión de plantillas de misiones diarias
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.db import get_db
from app.models import MissionTemplate
from app.schemas import (
    MissionTemplateCreate,
    MissionTemplateUpdate,
    MissionTemplateResponse,
    MissionTemplateListResponse
)

router = APIRouter(prefix="/mission-templates", tags=["Mission Templates"])


@router.get("", response_model=MissionTemplateListResponse)
def get_mission_templates(
    active_only: bool = Query(True, description="Solo plantillas activas"),
    learning_language: Optional[str] = Query(None, description="Filtrar por idioma de señas"),
    metric_type: Optional[str] = Query(None, description="Filtrar por tipo de métrica"),
    difficulty: Optional[str] = Query(None, description="Filtrar por dificultad"),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(50, ge=1, le=100, description="Tamaño de página"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de plantillas de misiones
    
    Filtros opcionales:
    - active_only: Solo activas (default: true)
    - learning_language: LSB, ASL, LSM, LIBRAS (filtra templates que incluyan este idioma o sean genéricos)
    - metric_type: exercises_completed, camera_minutes, etc.
    - difficulty: easy, medium, hard
    """
    query = db.query(MissionTemplate)
    
    if active_only:
        query = query.filter(MissionTemplate.active == True)
    
    if metric_type:
        query = query.filter(MissionTemplate.metric_type == metric_type)
    
    if difficulty:
        query = query.filter(
            or_(
                MissionTemplate.difficulty == difficulty,
                MissionTemplate.difficulty == None  # Null = aplica a todas
            )
        )
    
    if learning_language:
        # Filtrar por:
        # 1. learning_languages está vacío (aplica a todos)
        # 2. learning_language está en el array
        # PostgreSQL array overlap operator
        query = query.filter(
            or_(
                MissionTemplate.learning_languages == [],
                MissionTemplate.learning_languages.overlap([learning_language])
            )
        )
    
    # Count total
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    templates = query.order_by(
        MissionTemplate.priority.desc(),
        MissionTemplate.id
    ).offset(offset).limit(page_size).all()
    
    return MissionTemplateListResponse(
        templates=[MissionTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{template_id}", response_model=MissionTemplateResponse)
def get_mission_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Obtener una plantilla específica por ID"""
    template = db.query(MissionTemplate).filter(MissionTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template {template_id} not found"
        )
    
    return MissionTemplateResponse.model_validate(template)


@router.get("/code/{code}", response_model=MissionTemplateResponse)
def get_mission_template_by_code(
    code: str,
    db: Session = Depends(get_db)
):
    """Obtener una plantilla específica por código"""
    template = db.query(MissionTemplate).filter(MissionTemplate.code == code).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template with code '{code}' not found"
        )
    
    return MissionTemplateResponse.model_validate(template)


@router.post("", response_model=MissionTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_mission_template(
    template_data: MissionTemplateCreate,
    db: Session = Depends(get_db)
):
    """
    Crear nueva plantilla de misión
    
    Validaciones:
    - code debe ser único
    - title y description deben tener {es, en, pt}
    - metric_type debe ser válido
    - learning_languages deben ser válidos
    """
    # Check if code already exists
    existing = db.query(MissionTemplate).filter(MissionTemplate.code == template_data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mission template with code '{template_data.code}' already exists"
        )
    
    # Convert Pydantic models to dict for JSONB fields
    template_dict = template_data.model_dump()
    template_dict['title'] = template_data.title.model_dump()
    template_dict['description'] = template_data.description.model_dump()
    
    # Create template
    new_template = MissionTemplate(**template_dict)
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return MissionTemplateResponse.model_validate(new_template)


@router.put("/{template_id}", response_model=MissionTemplateResponse)
def update_mission_template(
    template_id: int,
    template_data: MissionTemplateUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar plantilla de misión existente
    
    Solo actualiza campos proporcionados (PATCH-like behavior)
    """
    template = db.query(MissionTemplate).filter(MissionTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template {template_id} not found"
        )
    
    # Update only provided fields
    update_data = template_data.model_dump(exclude_unset=True)
    
    # Convert Pydantic models to dict for JSONB fields
    if 'title' in update_data and update_data['title']:
        update_data['title'] = update_data['title']
    if 'description' in update_data and update_data['description']:
        update_data['description'] = update_data['description']
    
    for field, value in update_data.items():
        setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return MissionTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Eliminar plantilla de misión
    
    Nota: Esto NO afecta misiones ya generadas para usuarios.
    """
    template = db.query(MissionTemplate).filter(MissionTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template {template_id} not found"
        )
    
    db.delete(template)
    db.commit()
    
    return None


@router.patch("/{template_id}/activate", response_model=MissionTemplateResponse)
def activate_mission_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Activar una plantilla de misión"""
    template = db.query(MissionTemplate).filter(MissionTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template {template_id} not found"
        )
    
    template.active = True
    db.commit()
    db.refresh(template)
    
    return MissionTemplateResponse.model_validate(template)


@router.patch("/{template_id}/deactivate", response_model=MissionTemplateResponse)
def deactivate_mission_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Desactivar una plantilla de misión"""
    template = db.query(MissionTemplate).filter(MissionTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission template {template_id} not found"
        )
    
    template.active = False
    db.commit()
    db.refresh(template)
    
    return MissionTemplateResponse.model_validate(template)
