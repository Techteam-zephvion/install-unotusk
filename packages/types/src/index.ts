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
