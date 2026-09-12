import { ApiError, AuthResponse, Organization, Project } from '@unotusk/types';

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
};
