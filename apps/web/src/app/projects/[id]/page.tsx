'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Calendar,
  Layers,
  GitBranch,
  RotateCw,
  FileCode,
  Box,
  Link2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Play,
  KeyRound,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import {
  CodeDependency,
  CodeSymbol,
  Organization,
  Project,
  ProjectRepositoryContext,
  RepositoryFile,
  User,
} from '@unotusk/types';

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [context, setContext] = useState<ProjectRepositoryContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Connection dialog state
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [connecting, setConnecting] = useState(false);
  const [availableRepos, setAvailableRepos] = useState<any[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');

  // Active tab in completed context
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'symbols' | 'dependencies'>('overview');
  const [filesList, setFilesList] = useState<RepositoryFile[]>([]);
  const [symbolsList, setSymbolsList] = useState<CodeSymbol[]>([]);
  const [dependenciesList, setDependenciesList] = useState<CodeDependency[]>([]);
  const [loadingTab, setLoadingTab] = useState(false);

  // Ingestion polling ref
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const me = await api.auth.me();
      setUser(me.user);
      setOrganizations(me.organizations);

      const p = await api.projects.get(projectId);
      setProject(p);

      const ctx = await api.repository.getContext(projectId);
      setContext(ctx);

      // If snapshot is active, poll for progress
      const snap = ctx.active_snapshot;
      if (snap && ['QUEUED', 'CLONING', 'SCANNING', 'PARSING', 'INDEXING'].includes(snap.status)) {
        startPolling(snap.id);
      } else {
        stopPolling();
      }
    } catch (err: any) {
      if (err.status === 401) {
        router.push('/login');
        return;
      }
      setError(err.message || 'Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const startPolling = (snapshotId: string) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const snap = await api.repository.getIngestionStatus(projectId, snapshotId);
        setContext((prev) => (prev ? { ...prev, active_snapshot: snap } : prev));

        if (snap.status === 'COMPLETED' || snap.status === 'FAILED') {
          stopPolling();
          // Reload full context to populate metrics
          const updatedCtx = await api.repository.getContext(projectId);
          setContext(updatedCtx);
          const p = await api.projects.get(projectId);
          setProject(p);
        }
      } catch (e) {
        console.error('Polling error:', e);
      }
    }, 2000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  useEffect(() => {
    if (projectId) {
      loadData();
    }
    return () => stopPolling();
  }, [projectId]);

  // Lazy load tab data
  useEffect(() => {
    if (!context?.active_snapshot || context.active_snapshot.status !== 'COMPLETED') return;

    if (activeTab === 'files' && filesList.length === 0) {
      setLoadingTab(true);
      api.repository.listFiles(projectId).then(setFilesList).finally(() => setLoadingTab(false));
    } else if (activeTab === 'symbols' && symbolsList.length === 0) {
      setLoadingTab(true);
      api.repository.listSymbols(projectId).then(setSymbolsList).finally(() => setLoadingTab(false));
    } else if (activeTab === 'dependencies' && dependenciesList.length === 0) {
      setLoadingTab(true);
      api.repository.listDependencies(projectId).then(setDependenciesList).finally(() => setLoadingTab(false));
    }
  }, [activeTab, context?.active_snapshot]);

  // Connect GitHub & fetch repos
  const handleConnectGitHub = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    setError(null);
    try {
      await api.repository.connectGitHub(projectId, githubToken.trim() || undefined);
      const repos = await api.repository.listRepositories(projectId);
      setAvailableRepos(repos);
      if (repos.length > 0) {
        setSelectedRepoId(repos[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to connect to GitHub');
    } finally {
      setConnecting(false);
    }
  };

  // Select Repo
  const handleSelectRepo = async () => {
    const chosen = availableRepos.find((r) => r.id === selectedRepoId);
    if (!chosen) return;

    setConnecting(true);
    setError(null);
    try {
      await api.repository.selectRepository(projectId, {
        external_id: chosen.id,
        owner: chosen.owner,
        name: chosen.name,
        full_name: chosen.full_name,
        default_branch: chosen.default_branch,
        url: chosen.url,
        is_private: chosen.is_private,
        description: chosen.description,
      });
      setShowConnectModal(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to link repository');
    } finally {
      setConnecting(false);
    }
  };

  // Trigger Ingest / Re-index
  const handleTriggerIngest = async () => {
    if (!context?.repository) return;
    setError(null);
    try {
      const res = await api.repository.triggerIngest(projectId, context.repository.id);
      startPolling(res.snapshot_id);
      // Optimistic status update
      setContext((prev) =>
        prev
          ? {
              ...prev,
              active_snapshot: {
                id: res.snapshot_id,
                repository_id: context.repository!.id,
                commit_sha: null,
                branch: context.repository!.default_branch,
                status: 'QUEUED',
                total_files: 0,
                processed_files: 0,
                failed_files: 0,
                error_message: null,
                started_at: null,
                completed_at: null,
                created_at: new Date().toISOString(),
              },
            }
          : prev
      );
    } catch (err: any) {
      setError(err.message || 'Failed to trigger ingestion');
    }
  };

  const org = organizations.find((o) => o.id === project?.organization_id);
  const repo = context?.repository;
  const snapshot = context?.active_snapshot;
  const metrics = context?.metrics;

  const isIngesting =
    snapshot && ['QUEUED', 'CLONING', 'SCANNING', 'PARSING', 'INDEXING'].includes(snapshot.status);

  const progressPercent =
    snapshot && snapshot.total_files > 0
      ? Math.min(100, Math.round((snapshot.processed_files / snapshot.total_files) * 100))
      : 0;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar
        organizations={organizations}
        activeOrgId={project?.organization_id}
        userEmail={user?.email}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <Link
          href="/projects"
          className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to projects</span>
        </Link>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            Loading project details...
          </div>
        ) : !project ? (
          <div className="text-center py-16">
            <h2 className="text-base font-semibold">Project not found</h2>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                        project.status === 'READY'
                          ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                          : 'bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                      }`}
                    >
                      {project.status}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">
                      slug: {project.slug}
                    </span>
                  </div>
                  <h1 className="text-2xl font-bold tracking-tight text-foreground">
                    {project.name}
                  </h1>
                  <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
                    {project.description || 'No description provided.'}
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 text-xs text-muted-foreground border-t md:border-t-0 pt-4 md:pt-0 border-border">
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-muted-foreground" />
                    <span>Org: {org?.name || project.organization_id}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-muted-foreground" />
                    <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* STAGE 1: REPOSITORY CONNECTION & INGESTION STATE MACHINE */}
            {!repo ? (
              /* State 1: Before Connection */
              <div className="border border-border rounded-xl bg-card p-6 shadow-sm">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-foreground">
                      <GitBranch className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-foreground">Connect Repository</h2>
                      <p className="text-xs text-muted-foreground">
                        Select a GitHub repository to begin structured project ingestion.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="p-6 bg-muted/20 border border-dashed border-border rounded-xl text-center">
                  <GitBranch className="w-10 h-10 mx-auto text-muted-foreground stroke-1 mb-2" />
                  <p className="text-xs text-muted-foreground max-w-md mx-auto mb-4">
                    Connect your GitHub account or provide a repository access token to ingest files, AST symbols, and dependency relationships.
                  </p>
                  <button
                    onClick={() => setShowConnectModal(true)}
                    className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    <span>Connect GitHub</span>
                  </button>
                </div>
              </div>
            ) : isIngesting ? (
              /* State 3: During Ingestion */
              <div className="border border-blue-200 dark:border-blue-900 bg-blue-50/40 dark:bg-blue-950/20 rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <RotateCw className="w-5 h-5 text-blue-600 animate-spin" />
                    <div>
                      <h2 className="text-base font-bold text-foreground">
                        Analyzing project... ({snapshot?.status})
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        Ingesting {repo.full_name} on branch {repo.default_branch}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm font-mono font-bold text-blue-600">
                    {progressPercent}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-border h-2.5 rounded-full overflow-hidden mb-4">
                  <div
                    className="bg-blue-600 h-full transition-all duration-300 rounded-full"
                    style={{ width: `${Math.max(5, progressPercent)}%` }}
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                  <div className="p-3 bg-card border border-border rounded-lg">
                    <span className="text-muted-foreground block">Files discovered</span>
                    <span className="text-base font-bold text-foreground mt-0.5 block">
                      {snapshot?.total_files || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-card border border-border rounded-lg">
                    <span className="text-muted-foreground block">Files processed</span>
                    <span className="text-base font-bold text-foreground mt-0.5 block">
                      {snapshot?.processed_files || 0}
                    </span>
                  </div>
                  <div className="p-3 bg-card border border-border rounded-lg col-span-2 sm:col-span-1">
                    <span className="text-muted-foreground block">Current phase</span>
                    <span className="text-base font-mono font-bold text-blue-600 mt-0.5 block">
                      {snapshot?.status}
                    </span>
                  </div>
                </div>
              </div>
            ) : snapshot && snapshot.status === 'COMPLETED' ? (
              /* State 4: After Completion - Project Context Foundation */
              <div className="space-y-6">
                <div className="border border-border rounded-xl bg-card p-6 shadow-sm">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h2 className="text-lg font-bold text-foreground">Project Context</h2>
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="w-3 h-3" /> Indexed
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground flex items-center gap-2">
                        <span>Repository: <strong>{repo.full_name}</strong></span>
                        <span>•</span>
                        <span>Branch: <strong>{repo.default_branch}</strong></span>
                        {snapshot.commit_sha && (
                          <>
                            <span>•</span>
                            <span className="font-mono">
                              commit: {snapshot.commit_sha.slice(0, 7)}
                            </span>
                          </>
                        )}
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      {snapshot.completed_at && (
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          {new Date(snapshot.completed_at).toLocaleTimeString()}
                        </span>
                      )}
                      <button
                        onClick={handleTriggerIngest}
                        className="inline-flex items-center space-x-1.5 bg-secondary hover:bg-muted text-foreground text-xs font-semibold px-3 py-2 rounded-lg border border-border transition-colors shadow-sm"
                      >
                        <RotateCw className="w-3.5 h-3.5" />
                        <span>Re-index</span>
                      </button>
                    </div>
                  </div>

                  {/* Context Metrics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
                    <div className="p-4 bg-muted/20 border border-border rounded-xl">
                      <div className="flex items-center justify-between text-muted-foreground mb-1">
                        <span className="text-xs font-medium">Files</span>
                        <FileCode className="w-4 h-4" />
                      </div>
                      <span className="text-2xl font-bold tracking-tight text-foreground">
                        {metrics?.total_files?.toLocaleString() || 0}
                      </span>
                    </div>

                    <div className="p-4 bg-muted/20 border border-border rounded-xl">
                      <div className="flex items-center justify-between text-muted-foreground mb-1">
                        <span className="text-xs font-medium">Languages</span>
                        <Layers className="w-4 h-4" />
                      </div>
                      <span className="text-2xl font-bold tracking-tight text-foreground">
                        {metrics?.languages_count || 0}
                      </span>
                    </div>

                    <div className="p-4 bg-muted/20 border border-border rounded-xl">
                      <div className="flex items-center justify-between text-muted-foreground mb-1">
                        <span className="text-xs font-medium">Symbols</span>
                        <Box className="w-4 h-4" />
                      </div>
                      <span className="text-2xl font-bold tracking-tight text-foreground">
                        {metrics?.symbols_count?.toLocaleString() || 0}
                      </span>
                    </div>

                    <div className="p-4 bg-muted/20 border border-border rounded-xl">
                      <div className="flex items-center justify-between text-muted-foreground mb-1">
                        <span className="text-xs font-medium">Dependencies</span>
                        <Link2 className="w-4 h-4" />
                      </div>
                      <span className="text-2xl font-bold tracking-tight text-foreground">
                        {metrics?.dependencies_count?.toLocaleString() || 0}
                      </span>
                    </div>
                  </div>

                  {/* Language distribution pills */}
                  {metrics?.language_distribution && Object.keys(metrics.language_distribution).length > 0 && (
                    <div className="mt-6 pt-4 border-t border-border flex flex-wrap items-center gap-2">
                      <span className="text-xs text-muted-foreground mr-1">Languages:</span>
                      {Object.entries(metrics.language_distribution).map(([lang, count]) => (
                        <span
                          key={lang}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-muted text-foreground border border-border"
                        >
                          <span>{lang}</span>
                          <span className="text-muted-foreground font-mono text-[10px]">{count}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Structure Explorer Tabs */}
                <div className="border border-border rounded-xl bg-card shadow-sm overflow-hidden">
                  <div className="border-b border-border bg-muted/30 px-4 flex items-center space-x-4">
                    <button
                      onClick={() => setActiveTab('overview')}
                      className={`py-3 text-xs font-semibold border-b-2 transition-colors ${
                        activeTab === 'overview'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Context Summary
                    </button>
                    <button
                      onClick={() => setActiveTab('files')}
                      className={`py-3 text-xs font-semibold border-b-2 transition-colors ${
                        activeTab === 'files'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Discovered Files ({metrics?.total_files || 0})
                    </button>
                    <button
                      onClick={() => setActiveTab('symbols')}
                      className={`py-3 text-xs font-semibold border-b-2 transition-colors ${
                        activeTab === 'symbols'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Extracted Symbols ({metrics?.symbols_count || 0})
                    </button>
                    <button
                      onClick={() => setActiveTab('dependencies')}
                      className={`py-3 text-xs font-semibold border-b-2 transition-colors ${
                        activeTab === 'dependencies'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Dependencies ({metrics?.dependencies_count || 0})
                    </button>
                  </div>

                  <div className="p-6">
                    {loadingTab ? (
                      <div className="py-12 text-center text-xs text-muted-foreground">
                        Loading explorer details...
                      </div>
                    ) : activeTab === 'overview' ? (
                      <div className="space-y-4 text-xs text-muted-foreground">
                        <p>
                          Deterministic project context has been stored in PostgreSQL. AST analysis extracted symbols
                          and dependency trees via Tree-sitter.
                        </p>
                        <div className="p-4 bg-muted/20 border border-border rounded-lg text-xs space-y-1">
                          <div><strong>Repository:</strong> {repo.full_name}</div>
                          <div><strong>URL:</strong> <a href={repo.url} target="_blank" rel="noreferrer" className="text-blue-600 underline">{repo.url}</a></div>
                          <div><strong>Commit SHA:</strong> {snapshot.commit_sha}</div>
                          <div><strong>Parser Status:</strong> Completed with zero unhandled language crashes</div>
                        </div>
                      </div>
                    ) : activeTab === 'files' ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground">
                              <th className="pb-2 font-medium">Path</th>
                              <th className="pb-2 font-medium">Language</th>
                              <th className="pb-2 font-medium">Lines</th>
                              <th className="pb-2 font-medium">Size</th>
                              <th className="pb-2 font-medium">Parser</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {filesList.slice(0, 100).map((f) => (
                              <tr key={f.id} className="hover:bg-muted/30">
                                <td className="py-2 font-mono text-foreground font-medium">{f.path}</td>
                                <td className="py-2 text-muted-foreground">{f.language}</td>
                                <td className="py-2 font-mono">{f.line_count}</td>
                                <td className="py-2 font-mono text-muted-foreground">{(f.size_bytes / 1024).toFixed(1)} KB</td>
                                <td className="py-2">
                                  {f.parser_supported ? (
                                    <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-1.5 py-0.5 rounded">
                                      Parsed
                                    </span>
                                  ) : (
                                    <span className="text-[10px] text-muted-foreground">Skipped</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {filesList.length > 100 && (
                          <div className="text-center text-[11px] text-muted-foreground mt-4">
                            Showing first 100 of {filesList.length} files
                          </div>
                        )}
                      </div>
                    ) : activeTab === 'symbols' ? (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground">
                              <th className="pb-2 font-medium">Symbol</th>
                              <th className="pb-2 font-medium">Type</th>
                              <th className="pb-2 font-medium">Qualified Name</th>
                              <th className="pb-2 font-medium">File</th>
                              <th className="pb-2 font-medium">Lines</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {symbolsList.slice(0, 100).map((s) => (
                              <tr key={s.id} className="hover:bg-muted/30">
                                <td className="py-2 font-mono font-bold text-foreground">{s.name}</td>
                                <td className="py-2">
                                  <span className="text-[10px] font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950 px-1.5 py-0.5 rounded border border-blue-200 dark:border-blue-900">
                                    {s.symbol_type}
                                  </span>
                                </td>
                                <td className="py-2 font-mono text-muted-foreground">{s.qualified_name}</td>
                                <td className="py-2 font-mono text-[11px] text-foreground">{s.file_path || '—'}</td>
                                <td className="py-2 font-mono text-muted-foreground">L{s.start_line}-L{s.end_line}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {symbolsList.length > 100 && (
                          <div className="text-center text-[11px] text-muted-foreground mt-4">
                            Showing first 100 of {symbolsList.length} symbols
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-border text-muted-foreground">
                              <th className="pb-2 font-medium">Source File</th>
                              <th className="pb-2 font-medium">Import / Dependency</th>
                              <th className="pb-2 font-medium">Type</th>
                              <th className="pb-2 font-medium">Line</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {dependenciesList.slice(0, 100).map((d) => (
                              <tr key={d.id} className="hover:bg-muted/30">
                                <td className="py-2 font-mono text-foreground">{d.source_path || '—'}</td>
                                <td className="py-2 font-mono font-semibold text-foreground">
                                  {d.external_package || d.target_path || 'relative dependency'}
                                </td>
                                <td className="py-2 text-[10px] uppercase tracking-wider text-muted-foreground">
                                  {d.dependency_type}
                                </td>
                                <td className="py-2 font-mono text-muted-foreground">L{d.line_number}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {dependenciesList.length > 100 && (
                          <div className="text-center text-[11px] text-muted-foreground mt-4">
                            Showing first 100 of {dependenciesList.length} dependencies
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* State 2: Connected but not yet indexed */
              <div className="border border-border rounded-xl bg-card p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-start space-x-3">
                    <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-foreground mt-0.5">
                      <GitBranch className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-base font-bold text-foreground">{repo.full_name}</h2>
                        {repo.is_private && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                            Private
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Branch: <strong>{repo.default_branch}</strong> • Last indexed: —
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={handleTriggerIngest}
                    className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors shadow-sm self-start sm:self-auto"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Index Repository</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* GitHub Connect Modal */}
      {showConnectModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-lg w-full p-6 shadow-xl">
            <h2 className="text-lg font-bold text-foreground mb-1">Connect GitHub Repository</h2>
            <p className="text-xs text-muted-foreground mb-4">
              Enter a GitHub Personal Access Token (or leave blank to use the server default) to fetch your repositories.
            </p>

            {availableRepos.length === 0 ? (
              <form onSubmit={handleConnectGitHub} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold mb-1.5" htmlFor="token-input">
                    GitHub Personal Access Token <span className="text-muted-foreground font-normal">(Optional if GITHUB_TOKEN is set)</span>
                  </label>
                  <input
                    id="token-input"
                    type="password"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <span className="text-[11px] text-muted-foreground mt-1 block">
                    Requires read-only repository permissions (repo or fine-grained Contents: Read).
                  </span>
                </div>

                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={connecting}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {connecting ? 'Connecting...' : 'Fetch Repositories'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold mb-1.5">Select Repository</label>
                  <select
                    value={selectedRepoId}
                    onChange={(e) => setSelectedRepoId(e.target.value)}
                    className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {availableRepos.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.full_name} ({r.default_branch}) {r.is_private ? '[Private]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowConnectModal(false)}
                    className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSelectRepo}
                    disabled={connecting}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
                  >
                    {connecting ? 'Saving...' : 'Link Repository'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
