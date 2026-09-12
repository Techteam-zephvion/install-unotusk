import {
  ApiError,
  AuthResponse,
  CodeDependency,
  CodeSymbol,
  IngestTriggerResponse,
  Organization,
  Project,
  ProjectRepositoryContext,
  Repository,
  RepositoryFile,
  RepositorySnapshot,
} from '@unotusk/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiException extends Error {
  code: string;
  details?: unknown;
  status: number;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiException';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('unotusk_token');
}

export function setToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('unotusk_token', token);
  }
}

export function removeToken() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('unotusk_token');
    localStorage.removeItem('unotusk_active_org');
  }
}

export function getActiveOrg(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('unotusk_active_org');
}

export function setActiveOrg(orgId: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('unotusk_active_org', orgId);
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorPayload = data as ApiError;
    const code = errorPayload?.error?.code || 'UNKNOWN_ERROR';
    const message = errorPayload?.error?.message || response.statusText || 'An unexpected error occurred';
    throw new ApiException(code, message, response.status, errorPayload?.error?.details);
  }

  return data as T;
}

export const api = {
  auth: {
    signup: (payload: { email: string; name: string; password: string }) =>
      request<AuthResponse>('/api/v1/auth/signup', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    login: (payload: { email: string; password: string }) =>
      request<AuthResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    me: () =>
      request<{ user: AuthResponse['user']; organizations: Organization[] }>('/api/v1/auth/me'),
  },

  organizations: {
    list: () => request<Organization[]>('/api/v1/organizations'),
    create: (payload: { name: string; slug?: string }) =>
      request<Organization>('/api/v1/organizations', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    get: (id: string) => request<Organization>(`/api/v1/organizations/${id}`),
  },

  projects: {
    list: (orgId?: string) =>
      request<Project[]>(`/api/v1/projects${orgId ? `?organization_id=${orgId}` : ''}`),
    create: (payload: { organization_id: string; name: string; description?: string }) =>
      request<Project>('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    get: (id: string) => request<Project>(`/api/v1/projects/${id}`),
    delete: (id: string) =>
      request<void>(`/api/v1/projects/${id}`, {
        method: 'DELETE',
      }),
  },

  repository: {
    connectGitHub: (projectId: string, githubToken?: string) =>
      request<{ status: string; username?: string }>(`/api/v1/projects/${projectId}/github/connect`, {
        method: 'POST',
        body: JSON.stringify({ github_token: githubToken }),
      }),
    listRepositories: (projectId: string) =>
      request<any[]>(`/api/v1/projects/${projectId}/repositories`),
    selectRepository: (projectId: string, payload: any) =>
      request<Repository>(`/api/v1/projects/${projectId}/repositories/select`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    triggerIngest: (projectId: string, repositoryId: string) =>
      request<IngestTriggerResponse>(`/api/v1/projects/${projectId}/repositories/${repositoryId}/ingest`, {
        method: 'POST',
      }),
    getIngestionStatus: (projectId: string, ingestionId: string) =>
      request<RepositorySnapshot>(`/api/v1/projects/${projectId}/ingestions/${ingestionId}`),
    getContext: (projectId: string) =>
      request<ProjectRepositoryContext>(`/api/v1/projects/${projectId}/repository`),
    listFiles: (projectId: string) =>
      request<RepositoryFile[]>(`/api/v1/projects/${projectId}/files`),
    listSymbols: (projectId: string) =>
      request<CodeSymbol[]>(`/api/v1/projects/${projectId}/symbols`),
    listDependencies: (projectId: string) =>
      request<CodeDependency[]>(`/api/v1/projects/${projectId}/dependencies`),
    reindex: (projectId: string) =>
      request<IngestTriggerResponse>(`/api/v1/projects/${projectId}/repository/reindex`, {
        method: 'POST',
      }),
  },

  intelligence: {
    ask: (projectId: string, question: string, conversationId?: string) =>
      request<import('@unotusk/types').GroundedAnswerResponse>(`/api/v1/projects/${projectId}/ask`, {
        method: 'POST',
        body: JSON.stringify({ question, conversation_id: conversationId }),
      }),
    createConversation: (projectId: string, title?: string, initialQuestion?: string) =>
      request<import('@unotusk/types').Conversation>(`/api/v1/projects/${projectId}/conversations`, {
        method: 'POST',
        body: JSON.stringify({ title, initial_question: initialQuestion }),
      }),
    listConversations: (projectId: string) =>
      request<import('@unotusk/types').Conversation[]>(`/api/v1/projects/${projectId}/conversations`),
    getMessages: (projectId: string, conversationId: string) =>
      request<import('@unotusk/types').Message[]>(`/api/v1/projects/${projectId}/conversations/${conversationId}`),
    postMessage: (projectId: string, conversationId: string, question: string) =>
      request<import('@unotusk/types').GroundedAnswerResponse>(
        `/api/v1/projects/${projectId}/conversations/${conversationId}/messages`,
        {
          method: 'POST',
          body: JSON.stringify({ question }),
        }
      ),
    debugSearch: (projectId: string, query: string) =>
      request<import('@unotusk/types').ContextSearchResponse>(`/api/v1/projects/${projectId}/context/search`, {
        method: 'POST',
        body: JSON.stringify({ query }),
      }),
  },

  discovery: {
    listFindings: (
      projectId: string,
      filters?: {
        category?: string;
        severity?: string;
        status?: string;
        confidence?: string;
      }
    ) => {
      const params = new URLSearchParams();
      if (filters?.category) params.set('category', filters.category);
      if (filters?.severity) params.set('severity', filters.severity);
      if (filters?.status) params.set('status', filters.status);
      if (filters?.confidence) params.set('confidence', filters.confidence);
      const qs = params.toString();
      return request<import('@unotusk/types').Finding[]>(
        `/api/v1/projects/${projectId}/findings${qs ? `?${qs}` : ''}`
      );
    },
    getFinding: (projectId: string, findingId: string) =>
      request<import('@unotusk/types').Finding>(
        `/api/v1/projects/${projectId}/findings/${findingId}`
      ),
    updateStatus: (
      projectId: string,
      findingId: string,
      status: import('@unotusk/types').FindingStatus
    ) =>
      request<import('@unotusk/types').Finding>(
        `/api/v1/projects/${projectId}/findings/${findingId}`,
        {
          method: 'PATCH',
          body: JSON.stringify({ status }),
        }
      ),
    trigger: (projectId: string) =>
      request<import('@unotusk/types').DiscoveryTriggerResponse>(
        `/api/v1/projects/${projectId}/discover`,
        {
          method: 'POST',
        }
      ),
    getStatus: (projectId: string) =>
      request<import('@unotusk/types').DiscoverSummary>(
        `/api/v1/projects/${projectId}/discover/status`
      ),
  },
};
