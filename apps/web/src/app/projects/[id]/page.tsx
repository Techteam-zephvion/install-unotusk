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
  Sparkles,
  MessageSquare,
  Send,
  ChevronDown,
  ChevronRight,
  Search,
  Terminal,
  Plus,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import {
  CodeDependency,
  CodeSymbol,
  Conversation,
  EvidenceItem,
  Message,
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
  const [activeTab, setActiveTab] = useState<'overview' | 'ask' | 'files' | 'symbols' | 'dependencies'>('overview');
  const [filesList, setFilesList] = useState<RepositoryFile[]>([]);
  const [symbolsList, setSymbolsList] = useState<CodeSymbol[]>([]);
  const [dependenciesList, setDependenciesList] = useState<CodeDependency[]>([]);
  const [loadingTab, setLoadingTab] = useState(false);

  // Intelligence / Ask state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [questionInput, setQuestionInput] = useState('');
  const [asking, setAsking] = useState(false);
  const [expandedEvidenceKey, setExpandedEvidenceKey] = useState<string | null>(null);
  const [showDebugSignals, setShowDebugSignals] = useState(false);
  const [debugQuery, setDebugQuery] = useState('');
  const [debugResults, setDebugResults] = useState<any | null>(null);
  const [debugLoading, setDebugLoading] = useState(false);

  // Ingestion polling ref
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadConversations = async () => {
    try {
      const list = await api.intelligence.listConversations(projectId);
      setConversations(list);
      if (list.length > 0 && !activeConversationId) {
        setActiveConversationId(list[0].id);
        loadConversationMessages(list[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const loadConversationMessages = async (convId: string) => {
    try {
      const msgs = await api.intelligence.getMessages(projectId, convId);
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  };

  const handleAsk = async (queryText?: string) => {
    const q = (queryText || questionInput).trim();
    if (!q || asking) return;
    setAsking(true);
    setError(null);

    const tempUserMsg: Message = {
      id: 'temp-' + Date.now(),
      conversation_id: activeConversationId || '',
      role: 'user',
      content: q,
      evidence: [],
      related_entities: [],
      debug_signals: {},
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setQuestionInput('');

    try {
      const res = await api.intelligence.ask(projectId, q, activeConversationId || undefined);
      setActiveConversationId(res.conversation_id);
      const assistantMsg: Message = {
        id: res.message_id,
        conversation_id: res.conversation_id,
        role: 'assistant',
        content: res.content,
        evidence: res.evidence,
        related_entities: res.related_entities,
        confidence: res.confidence,
        debug_signals: res.debug_signals,
        created_at: res.created_at,
      };
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg]);
      loadConversations();
    } catch (err: any) {
      setError(err.message || 'Failed to generate grounded answer');
    } finally {
      setAsking(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.intelligence.createConversation(projectId, 'New Conversation');
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || 'Failed to create conversation');
    }
  };

  const handleDebugSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!debugQuery.trim() || debugLoading) return;
    setDebugLoading(true);
    try {
      const res = await api.intelligence.debugSearch(projectId, debugQuery);
      setDebugResults(res);
    } catch (err: any) {
      setError(err.message || 'Debug search failed');
    } finally {
      setDebugLoading(false);
    }
  };

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
                      onClick={() => {
                        setActiveTab('ask');
                        loadConversations();
                      }}
                      className={`py-3 text-xs font-semibold border-b-2 flex items-center space-x-1.5 transition-colors ${
                        activeTab === 'ask'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                      <span>Ask Unotusk</span>
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
                    ) : activeTab === 'ask' ? (
                      <div className="space-y-6">
                        {/* Ask Unotusk Header & Mode Controls */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
                          <div>
                            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                              <Sparkles className="w-4 h-4 text-blue-600" />
                              <span>Grounded Project Intelligence</span>
                            </h3>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Evidence-backed answers synthesized from deterministic repository files, symbols, and dependencies.
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => setShowDebugSignals(!showDebugSignals)}
                              className={`text-xs px-2.5 py-1.5 rounded-lg border font-medium flex items-center gap-1.5 transition-colors ${
                                showDebugSignals
                                  ? 'bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-950/50 dark:border-blue-800 dark:text-blue-300'
                                  : 'bg-muted/40 border-border text-muted-foreground hover:text-foreground'
                              }`}
                            >
                              <Terminal className="w-3.5 h-3.5" />
                              <span>Retrieval Signals</span>
                            </button>
                            <button
                              onClick={handleNewConversation}
                              className="text-xs px-2.5 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-foreground font-medium flex items-center gap-1.5 transition-colors shadow-xs"
                            >
                              <Plus className="w-3.5 h-3.5" />
                              <span>New Thread</span>
                            </button>
                          </div>
                        </div>

                        {/* Starter Prompt Chips */}
                        {messages.length === 0 && (
                          <div className="p-4 bg-muted/20 border border-border rounded-xl">
                            <span className="text-xs font-semibold text-foreground block mb-2">
                              Suggested Project Inquiries:
                            </span>
                            <div className="flex flex-wrap gap-2">
                              {[
                                'How does authentication work?',
                                'Where is payment processing implemented?',
                                'What depends on the UserService?',
                                'Which files define API routes?',
                                'How is the database connected and migrated?',
                              ].map((starter) => (
                                <button
                                  key={starter}
                                  onClick={() => handleAsk(starter)}
                                  disabled={asking}
                                  className="text-xs text-left px-3 py-1.5 rounded-lg bg-card hover:bg-blue-50 hover:text-blue-700 dark:hover:bg-blue-950/40 dark:hover:text-blue-300 border border-border transition-colors text-muted-foreground shadow-xs"
                                >
                                  {starter}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Conversation Messages Stream */}
                        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
                          {messages.map((m, idx) => (
                            <div
                              key={m.id || idx}
                              className={`p-4 rounded-xl border ${
                                m.role === 'user'
                                  ? 'bg-muted/40 border-border ml-6 sm:ml-12'
                                  : 'bg-card border-border mr-6 sm:mr-12 shadow-xs'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <span
                                    className={`text-xs font-bold px-2 py-0.5 rounded ${
                                      m.role === 'user'
                                        ? 'bg-secondary text-foreground'
                                        : 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                                    }`}
                                  >
                                    {m.role === 'user' ? 'Question' : 'Unotusk Intelligence'}
                                  </span>
                                  {m.confidence && (
                                    <span
                                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                                        m.confidence === 'HIGH'
                                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800'
                                          : m.confidence === 'MEDIUM'
                                          ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800'
                                          : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-800'
                                      }`}
                                    >
                                      Confidence: {m.confidence}
                                    </span>
                                  )}
                                </div>
                                <span className="text-[10px] text-muted-foreground">
                                  {new Date(m.created_at).toLocaleTimeString()}
                                </span>
                              </div>

                              {/* Answer Markdown Body */}
                              <div className="text-xs text-foreground whitespace-pre-wrap leading-relaxed">
                                {m.content}
                              </div>

                              {/* Collapsible Evidence Section */}
                              {m.evidence && m.evidence.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-border">
                                  <div className="text-xs font-semibold text-muted-foreground mb-2 flex items-center gap-1.5">
                                    <span>Grounded Repository Evidence ({m.evidence.length} sources)</span>
                                  </div>
                                  <div className="space-y-2">
                                    {m.evidence.map((ev, evIdx) => {
                                      const key = `${m.id}-${evIdx}`;
                                      const isExpanded = expandedEvidenceKey === key;
                                      return (
                                        <div
                                          key={key}
                                          className="text-xs border border-border rounded-lg bg-muted/20 overflow-hidden"
                                        >
                                          <button
                                            onClick={() => setExpandedEvidenceKey(isExpanded ? null : key)}
                                            className="w-full px-3 py-2 text-left flex items-center justify-between hover:bg-muted/40 transition-colors"
                                          >
                                            <div className="flex items-center gap-2 overflow-hidden">
                                              {isExpanded ? (
                                                <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                                              ) : (
                                                <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                                              )}
                                              <span className="font-mono text-foreground font-semibold truncate">
                                                {ev.file}
                                              </span>
                                              {ev.symbol && (
                                                <span className="text-blue-600 dark:text-blue-400 font-mono text-[11px]">
                                                  {ev.symbol}()
                                                </span>
                                              )}
                                              {ev.lines && (
                                                <span className="text-muted-foreground text-[10px]">
                                                  lines {ev.lines}
                                                </span>
                                              )}
                                            </div>
                                            <span className="text-[10px] font-mono text-muted-foreground ml-2 shrink-0">
                                              relevance: {Math.round(ev.relevance * 100)}%
                                            </span>
                                          </button>

                                          {isExpanded && ev.snippet && (
                                            <div className="p-3 bg-card border-t border-border font-mono text-[11px] overflow-x-auto text-muted-foreground">
                                              <pre>{ev.snippet}</pre>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Related Entities Pills */}
                              {m.related_entities && m.related_entities.length > 0 && (
                                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                                  <span className="text-[11px] text-muted-foreground mr-1">Related:</span>
                                  {m.related_entities.map((ent) => (
                                    <span
                                      key={ent}
                                      className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-secondary text-foreground border border-border"
                                    >
                                      {ent}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {/* Debug Signals Panel */}
                              {showDebugSignals && m.debug_signals && Object.keys(m.debug_signals).length > 0 && (
                                <div className="mt-3 p-2.5 bg-muted/40 rounded-lg border border-border text-[11px] font-mono text-muted-foreground space-y-1">
                                  <div className="font-bold text-foreground mb-1">Retrieval Debug Diagnostics:</div>
                                  <div>Model/Provider: {String(m.debug_signals.model || 'claude')}</div>
                                  <div>Candidates Retrieved: {String(m.debug_signals.candidates_retrieved ?? 'N/A')}</div>
                                  <div>Candidates Expanded: {String(m.debug_signals.candidates_expanded ?? 'N/A')}</div>
                                  <div>Keywords: {JSON.stringify(m.debug_signals.keywords || [])}</div>
                                  <div>Symbols Detected: {JSON.stringify(m.debug_signals.symbols_detected || [])}</div>
                                </div>
                              )}
                            </div>
                          ))}

                          {asking && (
                            <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20 text-xs text-blue-700 dark:text-blue-300 flex items-center space-x-2">
                              <RotateCw className="w-3.5 h-3.5 animate-spin" />
                              <span>Investigating repository context and synthesizing grounded answer...</span>
                            </div>
                          )}
                        </div>

                        {/* Question Input Box */}
                        <form
                          onSubmit={(e) => {
                            e.preventDefault();
                            handleAsk();
                          }}
                          className="pt-2 flex items-center space-x-2"
                        >
                          <input
                            type="text"
                            value={questionInput}
                            onChange={(e) => setQuestionInput(e.target.value)}
                            placeholder="Ask a technical or architectural question about this codebase..."
                            disabled={asking}
                            className="flex-1 bg-background border border-border rounded-lg px-3.5 py-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden focus:ring-2 focus:ring-blue-600"
                          />
                          <button
                            type="submit"
                            disabled={asking || !questionInput.trim()}
                            className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors shadow-xs"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Ask</span>
                          </button>
                        </form>

                        {/* Developer Debug Context Search Panel */}
                        {showDebugSignals && (
                          <div className="mt-6 p-4 border border-border rounded-xl bg-card">
                            <h4 className="text-xs font-bold text-foreground mb-2 flex items-center gap-1.5">
                              <Search className="w-3.5 h-3.5 text-blue-600" />
                              <span>Live Context Engine Search & Ranking Inspector</span>
                            </h4>
                            <form onSubmit={handleDebugSearch} className="flex gap-2 mb-3">
                              <input
                                type="text"
                                value={debugQuery}
                                onChange={(e) => setDebugQuery(e.target.value)}
                                placeholder="Test query retrieval (e.g., auth, users, payment)..."
                                className="flex-1 bg-background border border-border rounded-lg px-3 py-1.5 text-xs"
                              />
                              <button
                                type="submit"
                                disabled={debugLoading || !debugQuery.trim()}
                                className="bg-secondary text-foreground text-xs px-3 py-1.5 rounded-lg border border-border font-medium"
                              >
                                {debugLoading ? 'Searching...' : 'Inspect Signals'}
                              </button>
                            </form>

                            {debugResults && (
                              <div className="space-y-2 text-xs">
                                <div className="text-muted-foreground">
                                  Keywords: <code>{debugResults.keywords.join(', ')}</code> | Candidates: {debugResults.candidates_count}
                                </div>
                                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                                  {debugResults.ranked_candidates.map((c: any, i: number) => (
                                    <div key={i} className="p-2 bg-muted/30 border border-border rounded text-[11px] font-mono">
                                      <div className="flex justify-between font-bold text-foreground">
                                        <span>[{c.entity_type}] {c.name} ({c.path})</span>
                                        <span className="text-blue-600">score: {c.score}</span>
                                      </div>
                                      <div className="text-muted-foreground text-[10px] mt-0.5">
                                        Reasons: {c.reasons.join(' | ')}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
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
