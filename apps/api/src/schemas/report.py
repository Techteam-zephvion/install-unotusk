import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import KnowledgeClass, ReportStatus


class EvidenceRef(BaseModel):
    type: str = "CODE"
    file: str | None = None
    symbol: str | None = None
    lines: str | None = None
    snippet: str | None = None
    reference_type: str | None = None
    consumers_count: int | None = None


class ClaimItem(BaseModel):
    claim_type: KnowledgeClass = KnowledgeClass.OBSERVED
    title: str
    statement: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class VitalMetrics(BaseModel):
    total_files: int = 0
    total_symbols: int = 0
    total_dependencies: int = 0
    total_discoveries: int = 0
    critical_findings: int = 0
    high_findings: int = 0


class ExecutiveSummary(BaseModel):
    project_summary: str
    state_assessment: str
    vital_metrics: VitalMetrics
    top_things_to_know: list[ClaimItem] = Field(default_factory=list)
    top_next_actions: list[ClaimItem] = Field(default_factory=list)


class ProjectUnderstanding(BaseModel):
    primary_languages: dict[str, int] = Field(default_factory=dict)
    repository_size: dict[str, Any] = Field(default_factory=dict)
    major_areas: list[dict[str, Any]] = Field(default_factory=list)
    key_symbols: list[dict[str, Any]] = Field(default_factory=list)
    architectural_boundaries: list[str] = Field(default_factory=list)
    business_purpose_note: str


class TopDiscoveryItem(BaseModel):
    finding_id: str
    title: str
    category: str
    severity: str
    confidence: str
    what_we_found: str
    why_it_matters: str
    recommendation: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class RiskArea(BaseModel):
    area: str
    observed: list[ClaimItem] = Field(default_factory=list)
    derived: str
    recommended: str


class TechnicalDebtItem(BaseModel):
    signal: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    impact: str
    priority: str = "MEDIUM"


class ImportantDependency(BaseModel):
    source: str
    target: str
    dependency_type: str
    consumer_count: int = 0
    why_it_matters: str


class TestingAndDocs(BaseModel):
    testing_observed: list[ClaimItem] = Field(default_factory=list)
    testing_derived: str
    testing_recommended: str
    testing_coverage_note: str
    docs_observed: list[ClaimItem] = Field(default_factory=list)
    docs_recommended: str


class NextAction(BaseModel):
    id: str
    priority: str = "MEDIUM"
    title: str
    description: str
    claim_type: KnowledgeClass = KnowledgeClass.RECOMMENDED
    related_finding_ids: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ReportDocument(BaseModel):
    metadata: dict[str, Any]
    executive_summary: ExecutiveSummary
    project_understanding: ProjectUnderstanding
    observed: list[ClaimItem] = Field(default_factory=list)
    discoveries: list[TopDiscoveryItem] = Field(default_factory=list)
    risk_areas: list[RiskArea] = Field(default_factory=list)
    technical_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    dependencies: list[ImportantDependency] = Field(default_factory=list)
    testing_and_documentation: TestingAndDocs
    next_actions: list[NextAction] = Field(default_factory=list)


class ReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: uuid.UUID
    discovery_run_id: uuid.UUID | None
    status: ReportStatus
    report_version: str
    summary: str
    report_data: dict[str, Any]
    error_message: str | None
    generated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportListItemResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: uuid.UUID
    status: ReportStatus
    report_version: str
    summary: str
    generated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportTriggerResponse(BaseModel):
    task_id: str
    report_id: uuid.UUID
    status: ReportStatus
    message: str
