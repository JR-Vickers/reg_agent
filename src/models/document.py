"""Data models for regulatory documents and analysis."""

from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class RelevanceScore(int, Enum):
    """BSA/AML relevance scoring (0-5)."""
    NOT_RELEVANT = 0
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


class GapSeverity(str, Enum):
    """Gap analysis severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class BSAPillar(str, Enum):
    """BSA Five Pillars framework."""
    INTERNAL_CONTROLS = "internal_controls"
    BSA_OFFICER = "bsa_officer"
    TRAINING = "training"
    INDEPENDENT_TESTING = "independent_testing"
    CUSTOMER_DUE_DILIGENCE = "customer_due_diligence"


class DocumentSource(str, Enum):
    """Supported regulatory document sources."""
    FINCEN = "fincen"
    SEC = "sec"
    FEDERAL_REGISTER = "federal_register"
    CFTC = "cftc"
    NYDFS = "nydfs"
    OFAC = "ofac"


# Pydantic Models for API/Application Layer

class RegulationBase(BaseModel):
    """Base regulation document model."""
    source: DocumentSource
    document_id: str
    title: str
    url: str
    content: Optional[str] = None
    published_date: Optional[datetime] = None
    content_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator("content_hash")
    def validate_content_hash(cls, v):
        """Ensure content hash is SHA-256 format."""
        if v and len(v) != 64:
            raise ValueError("Content hash must be SHA-256 (64 characters)")
        return v


class RegulationCreate(RegulationBase):
    """Model for creating new regulations."""
    pass


class RegulationResponse(RegulationBase):
    """Model for regulation API responses."""
    id: UUID
    ingested_at: datetime

    class Config:
        from_attributes = True


class ClassificationBase(BaseModel):
    """Base classification model."""
    relevance_score: RelevanceScore
    confidence: float = Field(..., ge=0.0, le=1.0)
    bsa_pillars: Optional[List[BSAPillar]] = None
    categories: Optional[Dict[str, Any]] = None
    classification_reasoning: Optional[str] = None
    model_used: Optional[str] = None


class ClassificationCreate(ClassificationBase):
    """Model for creating new classifications."""
    regulation_id: UUID


class ClassificationResponse(ClassificationBase):
    """Model for classification API responses."""
    id: UUID
    regulation_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GapAnalysisBase(BaseModel):
    """Base gap analysis model."""
    affected_controls: Dict[str, Any]
    gap_severity: GapSeverity
    remediation_effort_hours: Optional[int] = Field(None, gt=0)
    similar_implementations: Optional[Dict[str, Any]] = None
    analysis_summary: str
    recommendations: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None


class GapAnalysisCreate(GapAnalysisBase):
    """Model for creating new gap analyses."""
    regulation_id: UUID


class GapAnalysisResponse(GapAnalysisBase):
    """Model for gap analysis API responses."""
    id: UUID
    regulation_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# Combined models for complex queries

class RegulationWithClassification(RegulationResponse):
    """Regulation with its classification."""
    classification: Optional[ClassificationResponse] = None


class RegulationWithAnalysis(RegulationResponse):
    """Regulation with classification and gap analysis."""
    classification: Optional[ClassificationResponse] = None
    gap_analysis: Optional[GapAnalysisResponse] = None


class PriorityRegulation(BaseModel):
    """High-priority regulation summary."""
    id: UUID
    source: DocumentSource
    title: str
    url: str
    published_date: Optional[datetime]
    relevance_score: Optional[RelevanceScore]
    confidence: Optional[float]
    gap_severity: Optional[GapSeverity]
    remediation_effort_hours: Optional[int]

    class Config:
        from_attributes = True


# Database Models (SQLAlchemy)

class Regulation(BaseModel):
    """Database model for regulations table."""
    id: UUID = Field(default_factory=uuid4)
    source: str
    document_id: str
    title: str
    url: str
    content: Optional[str] = None
    published_date: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None  # Vector embedding


class Classification(BaseModel):
    """Database model for classifications table."""
    id: UUID = Field(default_factory=uuid4)
    regulation_id: UUID
    relevance_score: int  # Stored as int in DB
    confidence: float
    bsa_pillars: Optional[Dict[str, Any]] = None
    categories: Optional[Dict[str, Any]] = None
    classification_reasoning: Optional[str] = None
    model_used: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GapAnalysis(BaseModel):
    """Database model for gap_analyses table."""
    id: UUID = Field(default_factory=uuid4)
    regulation_id: UUID
    affected_controls: Dict[str, Any]
    gap_severity: str
    remediation_effort_hours: Optional[int] = None
    similar_implementations: Optional[Dict[str, Any]] = None
    analysis_summary: str
    recommendations: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskBase(BaseModel):
    """Base task model."""
    control_id: str
    title: str
    description: Optional[str] = None
    assigned_team: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    """Model for creating new tasks."""
    regulation_id: UUID
    gap_analysis_id: UUID


class TaskUpdate(BaseModel):
    """Model for updating tasks."""
    status: Optional[TaskStatus] = None
    assigned_team: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class TaskResponse(TaskBase):
    """Model for task API responses."""
    id: UUID
    regulation_id: UUID
    gap_analysis_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Task(BaseModel):
    """Database model for tasks table."""
    id: UUID = Field(default_factory=uuid4)
    regulation_id: UUID
    gap_analysis_id: UUID
    control_id: str
    title: str
    description: Optional[str] = None
    assigned_team: str
    priority: str = "medium"
    status: str = "pending"
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)