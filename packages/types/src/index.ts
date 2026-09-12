export type MembershipRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export type ProjectStatus = 'CREATED' | 'CONNECTING' | 'READY' | 'ERROR';

export type IntegrationProvider = 'GITHUB';

export type IntegrationStatus = 'PENDING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR';

export type SnapshotStatus =
  | 'QUEUED'
  | 'CLONING'
  | 'SCANNING'
  | 'PARSING'
  | 'INDEXING'
  | 'COMPLETED'
  | 'FAILED';

export type SymbolType =
  | 'CLASS'
  | 'FUNCTION'
  | 'METHOD'
  | 'INTERFACE'
  | 'TYPE'
  | 'ENUM'
  | 'MODULE';

export type DependencyType = 'IMPORT' | 'REQUIRE' | 'FROM_IMPORT';

export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  role?: MembershipRole;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMembership {
  id: string;
  organization_id: string;
  user_id: string;
  role: MembershipRole;
  created_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface Integration {
  id: string;
  project_id: string;
  provider: IntegrationProvider;
  status: IntegrationStatus;
  external_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Repository {
  id: string;
  project_id: string;
  integration_id: string;
  provider: IntegrationProvider;
  external_id: string;
  owner: string;
  name: string;
  full_name: string;
  default_branch: string;
  url: string;
  is_private: boolean;
  repo_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RepositorySnapshot {
  id: string;
  repository_id: string;
  commit_sha: string | null;
  branch: string;
  status: SnapshotStatus;
  total_files: number;
  processed_files: number;
  failed_files: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface RepositoryFile {
  id: string;
  snapshot_id: string;
  path: string;
  filename: string;
  extension: string;
  language: string;
  size_bytes: number;
  content_hash: string;
  is_binary: boolean;
  is_generated: boolean;
  is_test: boolean;
  line_count: number;
  parser_supported: boolean;
}

export interface CodeSymbol {
  id: string;
  file_id: string;
  name: string;
  symbol_type: SymbolType;
  qualified_name: string;
  start_line: number;
  end_line: number;
  parent_symbol_id: string | null;
  file_path?: string;
  symbol_metadata: Record<string, unknown>;
}

export interface CodeDependency {
  id: string;
  source_file_id: string;
  target_file_id: string | null;
  external_package: string | null;
  dependency_type: DependencyType;
  line_number: number;
  source_path?: string;
  target_path?: string;
}

export interface ProjectContextMetrics {
  total_files: number;
  languages_count: number;
  symbols_count: number;
  dependencies_count: number;
  language_distribution: Record<string, number>;
}

export interface ProjectRepositoryContext {
  repository: Repository | null;
  active_snapshot: RepositorySnapshot | null;
  metrics: ProjectContextMetrics;
}

export interface IngestTriggerResponse {
  snapshot_id: string;
  status: SnapshotStatus;
  message: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  default_organization_id?: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// Stage 2: Grounded Project Intelligence Types
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface EvidenceItem {
  type: string;
  file: string;
  symbol: string | null;
  lines: string | null;
  relevance: number;
  snippet: string | null;
}

export interface GroundedAskRequest {
  question: string;
  conversation_id?: string;
}

export interface GroundedAnswerResponse {
  conversation_id: string;
  message_id: string;
  role: 'assistant';
  content: string;
  evidence: EvidenceItem[];
  related_entities: string[];
  confidence: ConfidenceLevel;
  debug_signals: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  evidence: EvidenceItem[];
  related_entities: string[];
  confidence?: ConfidenceLevel;
  debug_signals: Record<string, unknown>;
  created_at: string;
}

export interface ContextCandidateDebug {
  name: string;
  entity_type: string;
  path: string;
  lines: string;
  score: number;
  reasons: string[];
  snippet: string;
}

export interface ContextSearchResponse {
  query: string;
  keywords: string[];
  symbol_candidates: string[];
  candidates_count: number;
  ranked_candidates: ContextCandidateDebug[];
}

// Stage 3: Proactive Project Discovery Engine Types
export type FindingCategory =
  | 'UNUSED_CODE'
  | 'COUPLING'
  | 'DOCUMENTATION_GAP'
  | 'DUPLICATION'
  | 'ARCHITECTURE'
  | 'CIRCULAR_DEPENDENCY'
  | 'CHANGE_RISK'
  | 'LEGACY'
  | 'TEST_GAP';

export type FindingSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type FindingConfidence = 'HIGH' | 'MEDIUM' | 'LOW';

export type FindingStatus = 'OPEN' | 'ACKNOWLEDGED' | 'DISMISSED' | 'RESOLVED';

export type DiscoveryJobStatus =
  | 'QUEUED'
  | 'ANALYZING'
  | 'FINALIZING'
  | 'COMPLETED'
  | 'FAILED';

export interface Finding {
  id: string;
  project_id: string;
  snapshot_id: string;
  discovery_run_id?: string | null;
  category: FindingCategory;
  title: string;
  description: string;
  why_it_matters: string;
  severity: FindingSeverity;
  confidence: FindingConfidence;
  status: FindingStatus;
  score: number;
  recommendation: string;
  evidence: Array<{
    type: string;
    file?: string;
    target?: string;
    symbol?: string;
    lines?: string;
    snippet?: string;
    consumers_count?: number;
    [key: string]: unknown;
  }>;
  related_entities: string[];
  created_at: string;
  updated_at: string;
}

export interface DiscoveryRun {
  id: string;
  project_id: string;
  snapshot_id: string;
  status: DiscoveryJobStatus;
  progress: number;
  findings_count: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface DiscoverSummary {
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  latest_run?: DiscoveryRun | null;
}

export interface DiscoveryTriggerResponse {
  task_id: string;
  discovery_run_id: string;
  status: DiscoveryJobStatus;
  message: string;
}

// Stage 4: Project Intelligence Report Types
export type ReportStatus = 'QUEUED' | 'GENERATING' | 'COMPLETED' | 'FAILED';

export type KnowledgeClass = 'OBSERVED' | 'DERIVED' | 'CUSTOMER' | 'RECOMMENDED';

// Stage 5: Persistent Project Knowledge Types
export type KnowledgeCategory =
  | 'INTENT'
  | 'BUSINESS_RULE'
  | 'ARCHITECTURE_DECISION'
  | 'EXCEPTION'
  | 'CONSTRAINT'
  | 'LEGACY_CONTEXT'
  | 'CRITICAL_COMPONENT'
  | 'TEMPORARY_STATE'
  | 'OTHER';

export type KnowledgeStatus = 'ACTIVE' | 'ARCHIVED';

export interface ProjectKnowledge {
  id: string;
  project_id: string;
  created_by?: string | null;
  creator_email?: string | null;
  category: KnowledgeCategory;
  title: string;
  content: string;
  status: KnowledgeStatus;
  source_type: string;
  source_reference_type?: string | null;
  source_reference_id?: string | null;
  related_file_path?: string | null;
  related_symbol?: string | null;
  related_finding_id?: string | null;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  knowledge_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeCreateRequest {
  category: KnowledgeCategory;
  title: string;
  content: string;
  source_reference_type?: string | null;
  source_reference_id?: string | null;
  related_file_path?: string | null;
  related_symbol?: string | null;
  related_finding_id?: string | null;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  knowledge_metadata?: Record<string, unknown>;
}

export interface KnowledgeUpdateRequest {
  category?: KnowledgeCategory;
  title?: string;
  content?: string;
  status?: KnowledgeStatus;
  related_file_path?: string | null;
  related_symbol?: string | null;
  related_finding_id?: string | null;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  knowledge_metadata?: Record<string, unknown>;
}

export interface KnowledgeListResponse {
  items: ProjectKnowledge[];
  total: number;
}

export interface ReportEvidenceRef {
  type: string;
  file?: string | null;
  symbol?: string | null;
  lines?: string | null;
  snippet?: string | null;
  reference_type?: string | null;
  consumers_count?: number | null;
}

export interface ClaimItem {
  claim_type: KnowledgeClass;
  title: string;
  statement: string;
  evidence: ReportEvidenceRef[];
}

export interface VitalMetrics {
  total_files: number;
  total_symbols: number;
  total_dependencies: number;
  total_discoveries: number;
  critical_findings: number;
  high_findings: number;
}

export interface ExecutiveSummary {
  project_summary: string;
  state_assessment: string;
  vital_metrics: VitalMetrics;
  top_things_to_know: ClaimItem[];
  top_next_actions: ClaimItem[];
}

export interface ProjectUnderstanding {
  primary_languages: Record<string, number>;
  repository_size: {
    total_lines: number;
    total_bytes: number;
    size_formatted: string;
  };
  major_areas: Array<{
    area: string;
    files_count: number;
    sample_files: string[];
  }>;
  key_symbols: Array<{
    name: string;
    symbol_type: string;
    file_path: string;
    consumer_count: number;
  }>;
  architectural_boundaries: string[];
  business_purpose_note: string;
}

export interface TopDiscoveryItem {
  finding_id: string;
  title: string;
  category: string;
  severity: string;
  confidence: string;
  what_we_found: string;
  why_it_matters: string;
  recommendation: string;
  evidence: Array<Record<string, unknown>>;
}

export interface RiskArea {
  area: string;
  observed: ClaimItem[];
  derived: string;
  recommended: string;
}

export interface TechnicalDebtItem {
  signal: string;
  evidence: Array<Record<string, unknown>>;
  impact: string;
  priority: string;
}

export interface ImportantDependency {
  source: string;
  target: string;
  dependency_type: string;
  consumer_count: number;
  why_it_matters: string;
}

export interface TestingAndDocs {
  testing_observed: ClaimItem[];
  testing_derived: string;
  testing_recommended: string;
  testing_coverage_note: string;
  docs_observed: ClaimItem[];
  docs_recommended: string;
}

export interface NextAction {
  id: string;
  priority: string;
  title: string;
  description: string;
  claim_type: KnowledgeClass;
  related_finding_ids: string[];
  evidence: Array<Record<string, unknown>>;
}

export interface ReportDocument {
  metadata: Record<string, unknown>;
  executive_summary: ExecutiveSummary;
  project_understanding: ProjectUnderstanding;
  observed: ClaimItem[];
  discoveries: TopDiscoveryItem[];
  risk_areas: RiskArea[];
  technical_debt: TechnicalDebtItem[];
  dependencies: ImportantDependency[];
  testing_and_documentation: TestingAndDocs;
  next_actions: NextAction[];
  project_knowledge?: Array<Record<string, unknown>>;
}

export interface ProjectIntelligenceReport {
  id: string;
  project_id: string;
  snapshot_id: string;
  discovery_run_id?: string | null;
  status: ReportStatus;
  report_version: string;
  summary: string;
  report_data: ReportDocument;
  error_message?: string | null;
  generated_at: string;
  created_at: string;
}

export interface ReportListItem {
  id: string;
  project_id: string;
  snapshot_id: string;
  status: ReportStatus;
  report_version: string;
  summary: string;
  generated_at: string;
  created_at: string;
}

export interface ReportTriggerResponse {
  task_id: string;
  report_id: string;
  status: ReportStatus;
  message: string;
}

