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
  Compass,
  Lightbulb,
  ShieldAlert,
  SlidersHorizontal,
  X,
  Check,
  Eye,
  Filter,
  ArrowRight,
  FileText,
  Activity,
  CheckCircle,
  BookOpen,
  Archive,
  Edit3,
  Brain,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import {
  ClaimItem,
  CodeDependency,
  CodeSymbol,
  Conversation,
  DiscoverSummary,
  EvidenceItem,
  Finding,
  FindingCategory,
  FindingSeverity,
  FindingStatus,
  KnowledgeCategory,
  KnowledgeClass,
  KnowledgeStatus,
  Message,
  NextAction,
  Organization,
  Project,
  ProjectIntelligenceReport,
  ProjectKnowledge,
  ProjectRepositoryContext,
  ReportDocument,
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
  const [activeTab, setActiveTab] = useState<'overview' | 'reports' | 'discoveries' | 'knowledge' | 'ask' | 'files' | 'symbols' | 'dependencies'>('overview');
  const [filesList, setFilesList] = useState<RepositoryFile[]>([]);
  const [symbolsList, setSymbolsList] = useState<CodeSymbol[]>([]);
  const [dependenciesList, setDependenciesList] = useState<CodeDependency[]>([]);
  const [loadingTab, setLoadingTab] = useState(false);

  // Stage 5: Project Knowledge state
  const [knowledgeList, setKnowledgeList] = useState<ProjectKnowledge[]>([]);
  const [loadingKnowledge, setLoadingKnowledge] = useState(false);
  const [knowledgeCategoryFilter, setKnowledgeCategoryFilter] = useState<string>('ALL');
  const [knowledgeStatusFilter, setKnowledgeStatusFilter] = useState<string>('ACTIVE');
  const [knowledgeSearchQuery, setKnowledgeSearchQuery] = useState<string>('');
  const [selectedKnowledge, setSelectedKnowledge] = useState<ProjectKnowledge | null>(null);

  // Add/Edit Knowledge Modal state
  const [showKnowledgeModal, setShowKnowledgeModal] = useState(false);
  const [editingKnowledgeId, setEditingKnowledgeId] = useState<string | null>(null);
  const [knowledgeFormCategory, setKnowledgeFormCategory] = useState<KnowledgeCategory>('ARCHITECTURE_DECISION');
  const [knowledgeFormTitle, setKnowledgeFormTitle] = useState('');
  const [knowledgeFormContent, setKnowledgeFormContent] = useState('');
  const [knowledgeFormFilePath, setKnowledgeFormFilePath] = useState('');
  const [knowledgeFormSymbol, setKnowledgeFormSymbol] = useState('');
  const [knowledgeFormFindingId, setKnowledgeFormFindingId] = useState<string | null>(null);
  const [savingKnowledge, setSavingKnowledge] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);

  // Stage 4: Intelligence Report state
  const [report, setReport] = useState<ProjectIntelligenceReport | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportSection, setReportSection] = useState<'summary' | 'understanding' | 'discoveries' | 'risks' | 'debt' | 'dependencies' | 'tests_docs' | 'actions' | 'knowledge'>('summary');
  const [inspectedEvidence, setInspectedEvidence] = useState<{ title: string; statement?: string; evidence: any[] } | null>(null);
  const reportPollingRef = useRef<NodeJS.Timeout | null>(null);

  // Stage 3: Discoveries state
  const [findings, setFindings] = useState<Finding[]>([]);
  const [discoverSummary, setDiscoverSummary] = useState<DiscoverSummary | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const discoveryPollingRef = useRef<NodeJS.Timeout | null>(null);

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

  // Stage 3: Discoveries helper methods
  const loadDiscoverSummary = async () => {
    try {
      const summary = await api.discovery.getStatus(projectId);
      setDiscoverSummary(summary);
      if (
        summary.latest_run &&
        ['QUEUED', 'ANALYZING', 'FINALIZING'].includes(summary.latest_run.status)
      ) {
        setAnalyzing(true);
        startDiscoveryPolling();
      } else {
        setAnalyzing(false);
      }
    } catch (e) {
      console.error('Failed to load discovery summary:', e);
    }
  };

  const loadFindings = async () => {
    setLoadingFindings(true);
    try {
      const list = await api.discovery.listFindings(projectId, {
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        severity: severityFilter !== 'ALL' ? severityFilter : undefined,
        category: categoryFilter !== 'ALL' ? categoryFilter : undefined,
      });
      setFindings(list);
    } catch (e) {
      console.error('Failed to load findings:', e);
    } finally {
      setLoadingFindings(false);
    }
  };

  const startDiscoveryPolling = () => {
    stopDiscoveryPolling();
    discoveryPollingRef.current = setInterval(async () => {
      try {
        const summary = await api.discovery.getStatus(projectId);
        setDiscoverSummary(summary);
        if (
          !summary.latest_run ||
          summary.latest_run.status === 'COMPLETED' ||
          summary.latest_run.status === 'FAILED'
        ) {
          stopDiscoveryPolling();
          setAnalyzing(false);
          loadFindings();
        }
      } catch (e) {
        console.error('Discovery polling error:', e);
      }
    }, 2000);
  };

  const stopDiscoveryPolling = () => {
    if (discoveryPollingRef.current) {
      clearInterval(discoveryPollingRef.current);
      discoveryPollingRef.current = null;
    }
  };

  const handleTriggerDiscovery = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      await api.discovery.trigger(projectId);
      startDiscoveryPolling();
    } catch (err: any) {
      setError(err.message || 'Failed to trigger discovery analysis');
      setAnalyzing(false);
    }
  };

  const handleUpdateFindingStatus = async (findingId: string, newStatus: FindingStatus) => {
    try {
      const updated = await api.discovery.updateStatus(projectId, findingId, newStatus);
      setFindings((prev) => prev.map((f) => (f.id === findingId ? updated : f)));
      if (selectedFinding && selectedFinding.id === findingId) {
        setSelectedFinding(updated);
      }
      loadDiscoverSummary();
    } catch (err: any) {
      setError(err.message || 'Failed to update finding status');
    }
  };

  const handleInvestigateFinding = (finding: Finding) => {
    setActiveTab('ask');
    setSelectedFinding(null);
    const prompt = `Investigate discovery finding: "${finding.title}". ${finding.why_it_matters} What is the root cause and how should we address it?`;
    handleAsk(prompt);
  };

  // Stage 5: Project Knowledge Handlers
  const loadKnowledge = async () => {
    setLoadingKnowledge(true);
    try {
      const res = await api.knowledge.list(projectId, {
        status: knowledgeStatusFilter !== 'ALL' ? knowledgeStatusFilter : undefined,
        category: knowledgeCategoryFilter !== 'ALL' ? knowledgeCategoryFilter : undefined,
        search: knowledgeSearchQuery.trim() || undefined,
      });
      setKnowledgeList(res.items || []);
    } catch (e) {
      console.error('Failed to load project knowledge:', e);
    } finally {
      setLoadingKnowledge(false);
    }
  };

  const openAddKnowledgeModal = (opts?: {
    findingId?: string;
    filePath?: string;
    symbol?: string;
    category?: KnowledgeCategory;
    title?: string;
    content?: string;
  }) => {
    setEditingKnowledgeId(null);
    setKnowledgeFormCategory(opts?.category || 'ARCHITECTURE_DECISION');
    setKnowledgeFormTitle(opts?.title || '');
    setKnowledgeFormContent(opts?.content || '');
    setKnowledgeFormFilePath(opts?.filePath || '');
    setKnowledgeFormSymbol(opts?.symbol || '');
    setKnowledgeFormFindingId(opts?.findingId || null);
    setKnowledgeError(null);
    setShowKnowledgeModal(true);
  };

  const openEditKnowledgeModal = (item: ProjectKnowledge) => {
    setEditingKnowledgeId(item.id);
    setKnowledgeFormCategory(item.category);
    setKnowledgeFormTitle(item.title);
    setKnowledgeFormContent(item.content);
    setKnowledgeFormFilePath(item.related_file_path || '');
    setKnowledgeFormSymbol(item.related_symbol || '');
    setKnowledgeFormFindingId(item.related_finding_id || null);
    setKnowledgeError(null);
    setShowKnowledgeModal(true);
  };

  const handleSaveKnowledge = async () => {
    if (!knowledgeFormTitle.trim() || !knowledgeFormContent.trim()) {
      setKnowledgeError('Title and content are required.');
      return;
    }
    setSavingKnowledge(true);
    setKnowledgeError(null);
    try {
      if (editingKnowledgeId) {
        await api.knowledge.update(projectId, editingKnowledgeId, {
          title: knowledgeFormTitle.trim(),
          content: knowledgeFormContent.trim(),
          category: knowledgeFormCategory,
          related_file_path: knowledgeFormFilePath.trim() || null,
          related_symbol: knowledgeFormSymbol.trim() || null,
          related_finding_id: knowledgeFormFindingId || null,
        });
      } else {
        await api.knowledge.create(projectId, {
          title: knowledgeFormTitle.trim(),
          content: knowledgeFormContent.trim(),
          category: knowledgeFormCategory,
          related_file_path: knowledgeFormFilePath.trim() || null,
          related_symbol: knowledgeFormSymbol.trim() || null,
          related_finding_id: knowledgeFormFindingId || null,
        });
      }
      setShowKnowledgeModal(false);
      loadKnowledge();
    } catch (err: any) {
      setKnowledgeError(err.message || 'Failed to save knowledge.');
    } finally {
      setSavingKnowledge(false);
    }
  };

  const handleArchiveKnowledge = async (id: string) => {
    try {
      await api.knowledge.archive(projectId, id);
      loadKnowledge();
    } catch (err: any) {
      alert(err.message || 'Failed to archive knowledge');
    }
  };

  const handleRestoreKnowledge = async (id: string) => {
    try {
      await api.knowledge.restore(projectId, id);
      loadKnowledge();
    } catch (err: any) {
      alert(err.message || 'Failed to restore knowledge');
    }
  };

  const loadLatestReport = async () => {
    setLoadingReport(true);
    try {
      const res = await api.reports.getLatest(projectId);
      setReport(res);
      if (res && (res.status === 'QUEUED' || res.status === 'GENERATING')) {
        setGeneratingReport(true);
        startReportPolling();
      } else {
        setGeneratingReport(false);
      }
    } catch (err: any) {
      if (err.status !== 404) {
        console.error('Failed to load latest report:', err);
      }
      setReport(null);
    } finally {
      setLoadingReport(false);
    }
  };

  const startReportPolling = () => {
    stopReportPolling();
    reportPollingRef.current = setInterval(async () => {
      try {
        const res = await api.reports.getLatest(projectId);
        setReport(res);
        if (res && res.status === 'COMPLETED') {
          setGeneratingReport(false);
          stopReportPolling();
        } else if (res && res.status === 'FAILED') {
          setGeneratingReport(false);
          stopReportPolling();
          setError('Report generation failed');
        }
      } catch (e) {
        console.error('Report polling error:', e);
      }
    }, 2000);
  };

  const stopReportPolling = () => {
    if (reportPollingRef.current) {
      clearInterval(reportPollingRef.current);
      reportPollingRef.current = null;
    }
  };

  const handleTriggerReport = async () => {
    setGeneratingReport(true);
    setError(null);
    try {
      const res = await api.reports.trigger(projectId);
      if (res.status === 'COMPLETED') {
        const full = await api.reports.get(projectId, res.report_id);
        setReport(full);
        setGeneratingReport(false);
      } else {
        startReportPolling();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to trigger report generation');
      setGeneratingReport(false);
    }
  };

  const handleInvestigateAction = (actionTitle: string, actionDetail?: string, evidence?: any[]) => {
    setActiveTab('ask');
    let prompt = `Investigate recommendation: "${actionTitle}".`;
    if (actionDetail) {
      prompt += ` ${actionDetail}`;
    }
    if (evidence && evidence.length > 0) {
      prompt += ` Referenced evidence: ${evidence.map((e) => e.file || e.symbol || e.target || '').filter(Boolean).join(', ')}.`;
    }
    prompt += ` Explain which components depend on it and what risks changes to it could create.`;
    handleAsk(prompt);
  };

  const getKnowledgeBadgeClass = (type?: string) => {
    switch (type) {
      case 'OBSERVED':
        return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
      case 'DERIVED':
        return 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30';
      case 'RECOMMENDED':
        return 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/30';
      default:
        return 'bg-zinc-500/10 text-zinc-600 border-zinc-500/30';
    }
  };

  const getKnowledgeBadgeLabel = (type?: string) => {
    switch (type) {
      case 'OBSERVED':
        return 'FACT';
      case 'DERIVED':
        return 'INTERPRETATION';
      case 'RECOMMENDED':
        return 'SUGGESTION';
      default:
        return type || 'INFO';
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

      // Load discoveries summary
      loadDiscoverSummary();

      // Load latest intelligence report
      loadLatestReport();

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
    return () => {
      stopPolling();
      stopDiscoveryPolling();
      stopReportPolling();
    };
  }, [projectId]);

  // Lazy load tab data
  useEffect(() => {
    if (activeTab === 'discoveries') {
      loadFindings();
    } else if (activeTab === 'reports') {
      loadLatestReport();
    } else if (activeTab === 'knowledge') {
      loadKnowledge();
    }
  }, [activeTab, statusFilter, severityFilter, categoryFilter, knowledgeStatusFilter, knowledgeCategoryFilter, knowledgeSearchQuery]);

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

  const getSeverityBadgeClass = (severity: FindingSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30';
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30';
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30';
      case 'LOW':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30';
      default:
        return 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/30';
    }
  };

  const getStatusBadgeClass = (status: FindingStatus) => {
    switch (status) {
      case 'OPEN':
        return 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800';
      case 'ACKNOWLEDGED':
        return 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800';
      case 'RESOLVED':
        return 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
      case 'DISMISSED':
        return 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700';
      default:
        return 'bg-zinc-100 text-zinc-600 border-zinc-200';
    }
  };

  const filteredFindings = findings.filter((f) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      f.title.toLowerCase().includes(q) ||
      f.description.toLowerCase().includes(q) ||
      f.category.toLowerCase().includes(q) ||
      (f.related_entities && f.related_entities.some((e) => e.toLowerCase().includes(q)))
    );
  });

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
                  <div className="border-b border-border bg-muted/30 px-4 flex items-center space-x-4 overflow-x-auto">
                    <button
                      onClick={() => {
                        setActiveTab('reports');
                        loadLatestReport();
                      }}
                      className={`py-3 text-xs font-semibold border-b-2 flex items-center space-x-1.5 transition-colors whitespace-nowrap ${
                        activeTab === 'reports'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5 text-blue-600" />
                      <span>Intelligence Report</span>
                      {report?.status === 'COMPLETED' && (
                        <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          Ready
                        </span>
                      )}
                    </button>
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
                        setActiveTab('discoveries');
                        loadFindings();
                        loadDiscoverSummary();
                      }}
                      className={`py-3 text-xs font-semibold border-b-2 flex items-center space-x-1.5 transition-colors ${
                        activeTab === 'discoveries'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <Compass className="w-3.5 h-3.5 text-blue-600" />
                      <span>Discoveries</span>
                      {discoverSummary && discoverSummary.total_findings > 0 && (
                        <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300">
                          {discoverSummary.total_findings}
                        </span>
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setActiveTab('knowledge');
                        loadKnowledge();
                      }}
                      className={`py-3 text-xs font-semibold border-b-2 flex items-center space-x-1.5 transition-colors whitespace-nowrap ${
                        activeTab === 'knowledge'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <BookOpen className="w-3.5 h-3.5 text-blue-600" />
                      <span>Project Knowledge</span>
                      {knowledgeList.length > 0 && (
                        <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
                          {knowledgeList.length}
                        </span>
                      )}
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
                    ) : activeTab === 'reports' ? (
                      <div className="space-y-6">
                        {loadingReport ? (
                          <div className="py-16 text-center space-y-3">
                            <RotateCw className="w-6 h-6 text-blue-600 animate-spin mx-auto" />
                            <p className="text-xs text-muted-foreground">Loading Project Intelligence Report...</p>
                          </div>
                        ) : generatingReport || (report && (report.status === 'QUEUED' || report.status === 'GENERATING')) ? (
                          <div className="py-16 text-center space-y-4 border border-blue-200 dark:border-blue-900 bg-blue-50/30 dark:bg-blue-950/20 rounded-xl p-8">
                            <RotateCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
                            <div>
                              <h3 className="text-sm font-bold text-foreground">
                                Generating Complete Project Intelligence Report...
                              </h3>
                              <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                                Assembling deterministic AST and dependency facts, ranking discoveries, and generating grounded recommendations. Status: <span className="font-mono font-semibold text-blue-600">{report?.status || 'GENERATING'}</span>
                              </p>
                            </div>
                          </div>
                        ) : !report || !report.report_data ? (
                          <div className="py-16 text-center space-y-4 border border-dashed border-border rounded-xl p-8 bg-muted/10">
                            <div className="w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-950 flex items-center justify-center text-blue-600 mx-auto">
                              <FileText className="w-6 h-6" />
                            </div>
                            <div>
                              <h3 className="text-base font-bold text-foreground">
                                Project Intelligence Report
                              </h3>
                              <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1">
                                Synthesize repository structure, AST symbols, dependencies, and Stage 3 discoveries into a concise, evidence-backed 5–10 minute briefing.
                              </p>
                            </div>
                            <button
                              onClick={handleTriggerReport}
                              disabled={generatingReport}
                              className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                            >
                              <Sparkles className="w-4 h-4" />
                              <span>Generate Intelligence Report</span>
                            </button>
                          </div>
                        ) : (
                          /* Full Flagship Intelligence Report Display */
                          <div className="space-y-6">
                            {/* Report Header */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-bold uppercase tracking-wider text-blue-600">PROJECT INTELLIGENCE</span>
                                  <span className="text-muted-foreground">•</span>
                                  <span className="text-xs font-semibold text-foreground">{project?.name}</span>
                                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                                    {report.report_data.executive_summary?.state_assessment || 'Moderate Risk'}
                                  </span>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1 flex flex-wrap items-center gap-2">
                                  <span>Last generated: <strong>{report.generated_at ? new Date(report.generated_at).toLocaleString() : 'Just now'}</strong></span>
                                  {snapshot?.commit_sha && (
                                    <>
                                      <span>•</span>
                                      <span>Snapshot: <code className="text-xs font-mono">{snapshot.commit_sha.slice(0, 7)}</code></span>
                                    </>
                                  )}
                                  <span>•</span>
                                  <span>Report: v{report.report_version || '1.0.0'}</span>
                                </p>
                              </div>

                              <div className="flex items-center gap-2">
                                <button
                                  onClick={handleTriggerReport}
                                  disabled={generatingReport}
                                  className="inline-flex items-center space-x-1.5 bg-secondary hover:bg-muted text-foreground text-xs font-semibold px-3 py-2 rounded-lg border border-border transition-colors shadow-xs disabled:opacity-50"
                                >
                                  <RotateCw className={`w-3.5 h-3.5 ${generatingReport ? 'animate-spin' : ''}`} />
                                  <span>Regenerate Report</span>
                                </button>
                              </div>
                            </div>

                            {/* Section Navigation Tabs */}
                            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-border text-xs">
                              {[
                                { id: 'summary', label: 'Summary' },
                                { id: 'understanding', label: 'Understanding' },
                                { id: 'discoveries', label: 'Discoveries' },
                                { id: 'risks', label: 'Risks' },
                                { id: 'debt', label: 'Technical Debt' },
                                { id: 'dependencies', label: 'Dependencies' },
                                { id: 'tests_docs', label: 'Tests & Docs' },
                                { id: 'actions', label: 'Next Actions' },
                                { id: 'knowledge', label: `Project Knowledge (${report.report_data.project_knowledge?.length || 0})` },
                              ].map((sec) => (
                                <button
                                  key={sec.id}
                                  onClick={() => setReportSection(sec.id as any)}
                                  className={`px-3 py-1.5 rounded-lg font-medium transition-colors whitespace-nowrap ${
                                    reportSection === sec.id
                                      ? 'bg-blue-600 text-white shadow-xs'
                                      : 'bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground'
                                  }`}
                                >
                                  {sec.label}
                                </button>
                              ))}
                            </div>

                            {/* Section 1: Executive Summary */}
                            {reportSection === 'summary' && (
                              <div className="space-y-6">
                                <div className="p-4 bg-muted/20 border border-border rounded-xl">
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                                    Executive Summary
                                  </h4>
                                  <p className="text-xs text-foreground leading-relaxed">
                                    {report.report_data.executive_summary?.project_summary}
                                  </p>
                                </div>

                                {/* Vital Metrics */}
                                <div>
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                                    Vital Metrics Analyzed
                                  </h4>
                                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                    <div className="p-4 bg-card border border-border rounded-xl">
                                      <div className="text-xs text-muted-foreground">Files Analyzed</div>
                                      <div className="text-2xl font-bold text-foreground mt-1">
                                        {report.report_data.executive_summary?.vital_metrics?.total_files?.toLocaleString() || 0}
                                      </div>
                                    </div>
                                    <div className="p-4 bg-card border border-border rounded-xl">
                                      <div className="text-xs text-muted-foreground">Symbols Extracted</div>
                                      <div className="text-2xl font-bold text-foreground mt-1">
                                        {report.report_data.executive_summary?.vital_metrics?.total_symbols?.toLocaleString() || 0}
                                      </div>
                                    </div>
                                    <div className="p-4 bg-card border border-border rounded-xl">
                                      <div className="text-xs text-muted-foreground">Dependencies Mapped</div>
                                      <div className="text-2xl font-bold text-foreground mt-1">
                                        {report.report_data.executive_summary?.vital_metrics?.total_dependencies?.toLocaleString() || 0}
                                      </div>
                                    </div>
                                    <div className="p-4 bg-card border border-border rounded-xl">
                                      <div className="text-xs text-muted-foreground">Discoveries Found</div>
                                      <div className="text-2xl font-bold text-foreground mt-1">
                                        {report.report_data.executive_summary?.vital_metrics?.total_discoveries?.toLocaleString() || 0}
                                      </div>
                                    </div>
                                  </div>
                                </div>

                                {/* Top Things To Know */}
                                <div>
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                                    Top Things To Know
                                  </h4>
                                  <div className="space-y-3">
                                    {report.report_data.executive_summary?.top_things_to_know?.map((item, idx) => (
                                      <div
                                        key={idx}
                                        className="p-4 bg-card border border-border rounded-xl flex flex-col sm:flex-row sm:items-start justify-between gap-3"
                                      >
                                        <div className="space-y-1.5 flex-1">
                                          <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-bold text-blue-600">
                                              {String(idx + 1).padStart(2, '0')}
                                            </span>
                                            <span className="text-xs font-bold text-foreground">
                                              {item.statement}
                                            </span>
                                            <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass(item.claim_type)}`}>
                                              {getKnowledgeBadgeLabel(item.claim_type)}
                                            </span>
                                          </div>
                                          {item.title && item.title !== item.statement && (
                                            <p className="text-xs text-muted-foreground">
                                              {item.title}
                                            </p>
                                          )}
                                        </div>

                                        <div className="flex items-center gap-2 self-end sm:self-auto">
                                          {item.evidence && item.evidence.length > 0 && (
                                            <button
                                              onClick={() =>
                                                setInspectedEvidence({
                                                  title: `Observation #${idx + 1}`,
                                                  statement: item.statement,
                                                  evidence: item.evidence || [],
                                                })
                                              }
                                              className="text-[11px] px-2.5 py-1 rounded bg-muted hover:bg-muted/80 text-foreground border border-border font-medium flex items-center gap-1"
                                            >
                                              <Eye className="w-3 h-3" />
                                              <span>Evidence ({item.evidence.length})</span>
                                            </button>
                                          )}
                                          <button
                                            onClick={() =>
                                              handleInvestigateAction(item.statement, item.title, item.evidence)
                                            }
                                            className="text-[11px] px-2.5 py-1 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 border border-blue-200 dark:border-blue-900 font-semibold flex items-center gap-1"
                                          >
                                            <Sparkles className="w-3 h-3" />
                                            <span>Investigate</span>
                                          </button>
                                          <button
                                            onClick={() =>
                                              openAddKnowledgeModal({
                                                title: `${item.title} context`,
                                                filePath: item.evidence?.[0]?.file || undefined,
                                                symbol: item.evidence?.[0]?.symbol || undefined,
                                              })
                                            }
                                            className="text-[11px] px-2.5 py-1 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 hover:bg-amber-100 border border-amber-200 dark:border-amber-900 font-semibold flex items-center gap-1"
                                            title="Add Project Knowledge"
                                          >
                                            <Brain className="w-3 h-3" />
                                            <span>Add Knowledge</span>
                                          </button>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {/* Next Actions Preview */}
                                {report.report_data.next_actions &&
                                  report.report_data.next_actions.length > 0 && (
                                    <div>
                                      <div className="flex items-center justify-between mb-3">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                          Immediate Next Actions
                                        </h4>
                                        <button
                                          onClick={() => setReportSection('actions')}
                                          className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
                                        >
                                          <span>View all actions</span>
                                          <ArrowRight className="w-3 h-3" />
                                        </button>
                                      </div>
                                      <div className="space-y-2">
                                        {report.report_data.next_actions.slice(0, 3).map((act, idx) => (
                                          <div
                                            key={act.id || idx}
                                            className="p-3 bg-muted/20 border border-border rounded-lg flex items-center justify-between gap-3 text-xs"
                                          >
                                            <div className="flex items-center gap-2.5">
                                              <span className="font-mono font-bold text-blue-600">
                                                {String(idx + 1).padStart(2, '0')}
                                              </span>
                                              <span className="font-medium text-foreground">{act.title}</span>
                                              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded border bg-red-500/10 text-red-600 border-red-500/30">
                                                {act.priority}
                                              </span>
                                            </div>
                                            <button
                                              onClick={() => handleInvestigateAction(act.title, act.description)}
                                              className="text-[11px] font-semibold text-blue-600 hover:underline flex items-center gap-1"
                                            >
                                              <Sparkles className="w-3 h-3" />
                                              <span>Investigate</span>
                                            </button>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                              </div>
                            )}

                            {/* Section 2: Project Understanding */}
                            {reportSection === 'understanding' && (
                              <div className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div className="p-4 bg-card border border-border rounded-xl space-y-2">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                      Repository Structure & Languages
                                    </h4>
                                    <p className="text-xs text-foreground">
                                      {report.report_data.project_understanding?.repository_size?.size_formatted || '—'} total volume ({report.report_data.project_understanding?.repository_size?.total_lines?.toLocaleString() || 0} lines).
                                    </p>
                                    <div className="flex flex-wrap gap-1.5 pt-2">
                                      {Object.entries(report.report_data.project_understanding?.primary_languages || {}).map(([lang, count]) => (
                                        <span
                                          key={lang}
                                          className="px-2 py-0.5 rounded text-[11px] font-medium bg-muted border border-border"
                                        >
                                          {lang}: {count} files
                                        </span>
                                      ))}
                                    </div>
                                  </div>

                                  <div className="p-4 bg-card border border-border rounded-xl space-y-2">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                      Major Application Areas
                                    </h4>
                                    <div className="space-y-1.5">
                                      {report.report_data.project_understanding?.major_areas?.map((area, idx) => (
                                        <div key={idx} className="text-xs text-foreground flex items-center justify-between">
                                          <span className="flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600" />
                                            <span className="font-semibold">{area.area}</span>
                                          </span>
                                          <span className="text-muted-foreground font-mono text-[11px]">{area.files_count} files</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>

                                <div className="p-4 bg-card border border-border rounded-xl space-y-3">
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                    Architectural Boundaries & Business Purpose
                                  </h4>
                                  {report.report_data.project_understanding?.architectural_boundaries &&
                                    report.report_data.project_understanding.architectural_boundaries.length > 0 && (
                                      <div className="space-y-1">
                                        <div className="text-[11px] font-semibold text-muted-foreground">Boundary Observations:</div>
                                        {report.report_data.project_understanding.architectural_boundaries.map((b, i) => (
                                          <p key={i} className="text-xs text-foreground">• {b}</p>
                                        ))}
                                      </div>
                                    )}
                                  {report.report_data.project_understanding?.business_purpose_note && (
                                    <div className="p-3 bg-muted/20 border border-border rounded-lg text-xs text-muted-foreground italic">
                                      <strong>Purpose Observation:</strong> {report.report_data.project_understanding.business_purpose_note}
                                    </div>
                                  )}
                                </div>

                                {/* Key Symbols */}
                                {report.report_data.project_understanding?.key_symbols &&
                                  report.report_data.project_understanding.key_symbols.length > 0 && (
                                    <div className="p-4 bg-card border border-border rounded-xl space-y-3">
                                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                        High-Centrality Key Symbols
                                      </h4>
                                      <div className="overflow-x-auto">
                                        <table className="w-full text-left text-xs">
                                          <thead>
                                            <tr className="border-b border-border text-muted-foreground">
                                              <th className="pb-2 font-medium">Symbol</th>
                                              <th className="pb-2 font-medium">Type</th>
                                              <th className="pb-2 font-medium">File Path</th>
                                              <th className="pb-2 font-medium">References</th>
                                            </tr>
                                          </thead>
                                          <tbody className="divide-y divide-border">
                                            {report.report_data.project_understanding.key_symbols.map((sym, idx) => (
                                              <tr key={idx} className="hover:bg-muted/30">
                                                <td className="py-2 font-mono font-bold text-foreground">{sym.name}</td>
                                                <td className="py-2">
                                                  <span className="text-[10px] font-semibold text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-950 px-1.5 py-0.5 rounded border border-blue-200 dark:border-blue-900">
                                                    {sym.symbol_type}
                                                  </span>
                                                </td>
                                                <td className="py-2 font-mono text-muted-foreground">{sym.file_path || '—'}</td>
                                                <td className="py-2 font-mono text-foreground font-semibold">
                                                  {sym.consumer_count} incoming
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    </div>
                                  )}
                              </div>
                            )}

                            {/* Section 3: Discoveries */}
                            {reportSection === 'discoveries' && (
                              <div className="space-y-6">
                                <div className="flex items-center justify-between pb-2 border-b border-border">
                                  <div>
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                      Top Discoveries
                                    </h4>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                      Ranked by severity, architectural risk, and evidence density.
                                    </p>
                                  </div>
                                  <button
                                    onClick={() => {
                                      setActiveTab('discoveries');
                                      loadFindings();
                                    }}
                                    className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
                                  >
                                    <span>View all discoveries in Discovery tab</span>
                                    <ArrowRight className="w-3 h-3" />
                                  </button>
                                </div>

                                <div className="space-y-4">
                                  {report.report_data.discoveries?.map((disc, idx) => (
                                    <div
                                      key={disc.finding_id || idx}
                                      className="p-5 bg-card border border-border rounded-xl space-y-3 shadow-xs"
                                    >
                                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                                        <div className="space-y-1">
                                          <div className="flex flex-wrap items-center gap-2">
                                            <span className="font-mono font-bold text-xs text-blue-600">
                                              #{idx + 1}
                                            </span>
                                            <h5 className="text-sm font-bold text-foreground">
                                              {disc.title}
                                            </h5>
                                            <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${getSeverityBadgeClass(disc.severity as FindingSeverity)}`}>
                                              {disc.severity}
                                            </span>
                                            <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border">
                                              {disc.category}
                                            </span>
                                            <span className="text-[10px] font-medium text-muted-foreground">
                                              Confidence: <strong>{disc.confidence}</strong>
                                            </span>
                                          </div>
                                        </div>

                                        <div className="flex items-center gap-2 self-end sm:self-auto">
                                          {disc.evidence && disc.evidence.length > 0 && (
                                            <button
                                              onClick={() =>
                                                setInspectedEvidence({
                                                  title: disc.title,
                                                  statement: disc.what_we_found,
                                                  evidence: disc.evidence || [],
                                                })
                                              }
                                              className="text-[11px] px-2.5 py-1 rounded bg-muted hover:bg-muted/80 text-foreground border border-border font-medium flex items-center gap-1"
                                            >
                                              <Eye className="w-3 h-3" />
                                              <span>Evidence ({disc.evidence.length})</span>
                                            </button>
                                          )}
                                          <button
                                            onClick={() =>
                                              handleInvestigateAction(disc.title, disc.why_it_matters, disc.evidence)
                                            }
                                            className="text-[11px] px-2.5 py-1 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 border border-blue-200 dark:border-blue-900 font-semibold flex items-center gap-1"
                                          >
                                            <Sparkles className="w-3 h-3" />
                                            <span>Investigate</span>
                                          </button>
                                          <button
                                            onClick={() =>
                                              openAddKnowledgeModal({
                                                findingId: disc.finding_id,
                                                title: `${disc.title} context`,
                                                filePath: (disc.evidence?.[0] as any)?.file_path || (disc.evidence?.[0] as any)?.file,
                                                symbol: (disc.evidence?.[0] as any)?.symbol,
                                              })
                                            }
                                            className="text-[11px] px-2.5 py-1 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 hover:bg-amber-100 border border-amber-200 dark:border-amber-900 font-semibold flex items-center gap-1"
                                            title="Add Project Knowledge"
                                          >
                                            <Brain className="w-3 h-3" />
                                            <span>Add Knowledge</span>
                                          </button>
                                        </div>
                                      </div>

                                      <div className="space-y-2 text-xs">
                                        <div>
                                          <span className="font-semibold text-muted-foreground">WHAT WE FOUND: </span>
                                          <span className="text-foreground">{disc.what_we_found}</span>
                                        </div>
                                        <div>
                                          <span className="font-semibold text-muted-foreground">WHY IT MATTERS: </span>
                                          <span className="text-foreground">{disc.why_it_matters}</span>
                                        </div>
                                        {disc.recommendation && (
                                          <div className="p-2.5 bg-muted/30 border border-border rounded-lg text-foreground">
                                            <span className="font-semibold text-purple-700 dark:text-purple-400">RECOMMENDATION: </span>
                                            <span>{disc.recommendation}</span>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Section 4: Risk Areas */}
                            {reportSection === 'risks' && (
                              <div className="space-y-6">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                  Risk Areas & Structural Hotspots
                                </h4>

                                <div className="grid grid-cols-1 gap-4">
                                  {report.report_data.risk_areas?.map((area, idx) => (
                                    <div key={idx} className="p-5 bg-card border border-border rounded-xl space-y-4 shadow-xs">
                                      <div className="border-b border-border pb-2.5">
                                        <h5 className="text-sm font-bold text-foreground flex items-center justify-between">
                                          <span>{area.area}</span>
                                        </h5>
                                      </div>

                                      <div className="space-y-2.5 text-xs">
                                        {/* Observed facts */}
                                        {area.observed?.map((obs, i) => (
                                          <div key={i} className="flex items-start justify-between gap-2 p-2 rounded bg-muted/20">
                                            <div className="space-y-0.5">
                                              <div className="flex items-center gap-1.5">
                                                <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('OBSERVED')}`}>
                                                  FACT
                                                </span>
                                                <span className="font-medium text-foreground">{obs.statement}</span>
                                              </div>
                                            </div>
                                            {obs.evidence && obs.evidence.length > 0 && (
                                              <button
                                                onClick={() =>
                                                  setInspectedEvidence({
                                                    title: `${area.area} - Observed Fact`,
                                                    statement: obs.statement,
                                                    evidence: obs.evidence || [],
                                                  })
                                                }
                                                className="text-[10px] text-blue-600 hover:underline font-mono"
                                              >
                                                Evidence ({obs.evidence.length})
                                              </button>
                                            )}
                                          </div>
                                        ))}

                                        {/* Derived interpretation */}
                                        {area.derived && (
                                          <div className="flex items-start justify-between gap-2 p-2 rounded bg-blue-50/20 dark:bg-blue-950/10 border border-blue-100 dark:border-blue-900/30">
                                            <div className="flex items-center gap-1.5">
                                              <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('DERIVED')}`}>
                                                INTERPRETATION
                                              </span>
                                              <span className="text-foreground">{area.derived}</span>
                                            </div>
                                          </div>
                                        )}

                                        {/* Recommended suggestion */}
                                        {area.recommended && (
                                          <div className="flex items-center justify-between gap-2 p-2 rounded bg-purple-50/20 dark:bg-purple-950/10 border border-purple-100 dark:border-purple-900/30">
                                            <div className="flex items-center gap-1.5">
                                              <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('RECOMMENDED')}`}>
                                                SUGGESTION
                                              </span>
                                              <span className="font-medium text-foreground">{area.recommended}</span>
                                            </div>
                                            <button
                                              onClick={() => handleInvestigateAction(area.recommended)}
                                              className="text-[10px] text-purple-700 dark:text-purple-400 font-semibold hover:underline"
                                            >
                                              Investigate
                                            </button>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Section 5: Technical Debt */}
                            {reportSection === 'debt' && (
                              <div className="space-y-6">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                  Technical Debt Signals
                                </h4>

                                <div className="overflow-x-auto border border-border rounded-xl bg-card">
                                  <table className="w-full text-left text-xs">
                                    <thead>
                                      <tr className="border-b border-border text-muted-foreground bg-muted/30">
                                        <th className="p-3 font-medium">Signal</th>
                                        <th className="p-3 font-medium">Priority</th>
                                        <th className="p-3 font-medium">Likely Impact</th>
                                        <th className="p-3 font-medium">Evidence</th>
                                        <th className="p-3 font-medium">Action</th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-border">
                                      {report.report_data.technical_debt?.map((td, idx) => (
                                        <tr key={idx} className="hover:bg-muted/30">
                                          <td className="p-3 font-semibold text-foreground">{td.signal}</td>
                                          <td className="p-3">
                                            <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded border ${
                                              td.priority === 'HIGH'
                                                ? 'bg-red-500/10 text-red-600 border-red-500/30'
                                                : td.priority === 'MEDIUM'
                                                ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                                                : 'bg-blue-500/10 text-blue-600 border-blue-500/30'
                                            }`}>
                                              {td.priority}
                                            </span>
                                          </td>
                                          <td className="p-3 text-muted-foreground">{td.impact}</td>
                                          <td className="p-3 font-mono text-[11px]">
                                            {td.evidence && td.evidence.length > 0 ? (
                                              <button
                                                onClick={() =>
                                                  setInspectedEvidence({
                                                    title: td.signal,
                                                    statement: td.impact,
                                                    evidence: td.evidence || [],
                                                  })
                                                }
                                                className="text-blue-600 hover:underline"
                                              >
                                                {td.evidence.length} reference(s)
                                              </button>
                                            ) : (
                                              '—'
                                            )}
                                          </td>
                                          <td className="p-3">
                                            <button
                                              onClick={() => handleInvestigateAction(td.signal, td.impact, td.evidence)}
                                              className="text-blue-600 hover:underline font-medium text-[11px]"
                                            >
                                              Investigate
                                            </button>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              </div>
                            )}

                            {/* Section 6: Dependencies */}
                            {reportSection === 'dependencies' && (
                              <div className="space-y-6">
                                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                  Important Dependency Hotspots & Relationships
                                </h4>

                                <div className="space-y-3">
                                  {report.report_data.dependencies?.map((dep, idx) => (
                                    <div
                                      key={idx}
                                      className="p-4 bg-card border border-border rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                                    >
                                      <div className="space-y-1">
                                        <div className="flex items-center gap-2">
                                          <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-muted text-muted-foreground border border-border uppercase">
                                            {dep.dependency_type}
                                          </span>
                                          <span className="font-mono font-bold text-foreground">
                                            {dep.source} {dep.target ? `→ ${dep.target}` : ''}
                                          </span>
                                          {dep.consumer_count > 0 && (
                                            <span className="text-[10px] text-blue-600 font-semibold">
                                              ({dep.consumer_count} consumers)
                                            </span>
                                          )}
                                        </div>
                                        <p className="text-muted-foreground">{dep.why_it_matters}</p>
                                      </div>

                                      <div className="flex items-center gap-2">
                                        <button
                                          onClick={() =>
                                            handleInvestigateAction(
                                              `Investigate dependency relationship: ${dep.source} ${dep.target ? '-> ' + dep.target : ''}`,
                                              dep.why_it_matters
                                            )
                                          }
                                          className="text-[11px] px-2.5 py-1 rounded bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 hover:bg-blue-100 border border-blue-200 dark:border-blue-900 font-semibold"
                                        >
                                          Investigate
                                        </button>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Section 7: Tests & Docs */}
                            {reportSection === 'tests_docs' && (
                              <div className="space-y-6">
                                <div className="p-5 bg-card border border-border rounded-xl space-y-4">
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                    Testing State & Coverage Gaps
                                  </h4>
                                  <div className="space-y-2 text-xs">
                                    {report.report_data.testing_and_documentation?.testing_observed?.map((item, i) => (
                                      <div key={i} className="flex items-center gap-2">
                                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('OBSERVED')}`}>
                                          FACT
                                        </span>
                                        <span className="text-foreground">{item.statement}</span>
                                      </div>
                                    ))}
                                    {report.report_data.testing_and_documentation?.testing_derived && (
                                      <div className="flex items-center gap-2">
                                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('DERIVED')}`}>
                                          INTERPRETATION
                                        </span>
                                        <span className="text-foreground">{report.report_data.testing_and_documentation.testing_derived}</span>
                                      </div>
                                    )}
                                    {report.report_data.testing_and_documentation?.testing_recommended && (
                                      <div className="flex items-center justify-between gap-2 p-2 rounded bg-purple-50/20 dark:bg-purple-950/10 border border-purple-100 dark:border-purple-900/30">
                                        <div className="flex items-center gap-2">
                                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('RECOMMENDED')}`}>
                                            SUGGESTION
                                          </span>
                                          <span className="font-medium text-foreground">{report.report_data.testing_and_documentation.testing_recommended}</span>
                                        </div>
                                        <button
                                          onClick={() => handleInvestigateAction(report.report_data.testing_and_documentation.testing_recommended)}
                                          className="text-[10px] font-semibold text-purple-700 dark:text-purple-400 hover:underline"
                                        >
                                          Investigate
                                        </button>
                                      </div>
                                    )}
                                    {report.report_data.testing_and_documentation?.testing_coverage_note && (
                                      <p className="text-[11px] text-muted-foreground italic pt-1">
                                        {report.report_data.testing_and_documentation.testing_coverage_note}
                                      </p>
                                    )}
                                  </div>
                                </div>

                                <div className="p-5 bg-card border border-border rounded-xl space-y-4">
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                    Documentation State & Interface Gaps
                                  </h4>
                                  <div className="space-y-2 text-xs">
                                    {report.report_data.testing_and_documentation?.docs_observed?.map((item, i) => (
                                      <div key={i} className="flex items-center gap-2">
                                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('OBSERVED')}`}>
                                          FACT
                                        </span>
                                        <span className="text-foreground">{item.statement}</span>
                                      </div>
                                    ))}
                                    {report.report_data.testing_and_documentation?.docs_recommended && (
                                      <div className="flex items-center justify-between gap-2 p-2 rounded bg-purple-50/20 dark:bg-purple-950/10 border border-purple-100 dark:border-purple-900/30">
                                        <div className="flex items-center gap-2">
                                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getKnowledgeBadgeClass('RECOMMENDED')}`}>
                                            SUGGESTION
                                          </span>
                                          <span className="font-medium text-foreground">{report.report_data.testing_and_documentation.docs_recommended}</span>
                                        </div>
                                        <button
                                          onClick={() => handleInvestigateAction(report.report_data.testing_and_documentation.docs_recommended)}
                                          className="text-[10px] font-semibold text-purple-700 dark:text-purple-400 hover:underline"
                                        >
                                          Investigate
                                        </button>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Section 8: Next Actions */}
                            {reportSection === 'actions' && (
                              <div className="space-y-6">
                                <div>
                                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">
                                    Prioritized Next Actions
                                  </h4>
                                  <p className="text-xs text-muted-foreground mb-4">
                                    Recommendations derived from repository evidence. Ready to investigate with Grounded Ask.
                                  </p>
                                </div>

                                <div className="space-y-3">
                                  {report.report_data.next_actions?.map((act, idx) => (
                                    <div
                                      key={act.id || idx}
                                      className="p-4 bg-card border border-border rounded-xl flex flex-col sm:flex-row sm:items-start justify-between gap-3 text-xs shadow-xs"
                                    >
                                      <div className="space-y-1.5 flex-1">
                                        <div className="flex items-center gap-2">
                                          <span className="font-mono font-bold text-blue-600">
                                            {String(idx + 1).padStart(2, '0')}
                                          </span>
                                          <h5 className="font-bold text-foreground text-sm">{act.title}</h5>
                                          <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                                            act.priority === 'HIGH'
                                              ? 'bg-red-500/10 text-red-600 border-red-500/30'
                                              : act.priority === 'MEDIUM'
                                              ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                                              : 'bg-blue-500/10 text-blue-600 border-blue-500/30'
                                          }`}>
                                            {act.priority}
                                          </span>
                                        </div>
                                        <p className="text-muted-foreground">{act.description}</p>
                                      </div>

                                      <button
                                        onClick={() => handleInvestigateAction(act.title, act.description)}
                                        className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors shadow-xs self-end sm:self-auto"
                                      >
                                        <Sparkles className="w-3.5 h-3.5" />
                                        <span>Investigate with Grounded Ask</span>
                                        <ArrowRight className="w-3 h-3 ml-0.5" />
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Section 9: Project Knowledge */}
                            {reportSection === 'knowledge' && (
                              <div className="space-y-6">
                                <div className="flex items-center justify-between pb-2 border-b border-border">
                                  <div>
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                      Project Knowledge (Contextualized into this Report)
                                    </h4>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                      Explicit customer context, intent, decisions, and constraints supplied to guide interpretation.
                                    </p>
                                  </div>
                                  <button
                                    onClick={() => {
                                      setActiveTab('knowledge');
                                      loadKnowledge();
                                    }}
                                    className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
                                  >
                                    <span>Manage Knowledge in Tab</span>
                                    <ArrowRight className="w-3 h-3" />
                                  </button>
                                </div>

                                {(!report.report_data.project_knowledge || report.report_data.project_knowledge.length === 0) ? (
                                  <div className="py-12 text-center border border-border border-dashed rounded-xl bg-muted/10 space-y-3">
                                    <Brain className="w-8 h-8 text-muted-foreground mx-auto stroke-1" />
                                    <div className="space-y-1">
                                      <h5 className="text-xs font-bold text-foreground">No customer knowledge recorded at generation time</h5>
                                      <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                                        Teach Unotusk about intentional architecture choices, business rules, or legacy context to enrich future reports.
                                      </p>
                                    </div>
                                    <button
                                      onClick={() => openAddKnowledgeModal()}
                                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
                                    >
                                      <Plus className="w-3.5 h-3.5" />
                                      <span>Add Project Knowledge</span>
                                    </button>
                                  </div>
                                ) : (
                                  <div className="space-y-3">
                                    {report.report_data.project_knowledge.map((k: any, idx: number) => (
                                      <div key={idx} className="p-4 bg-card border border-amber-500/20 rounded-xl space-y-2 shadow-xs">
                                        <div className="flex items-center justify-between gap-2">
                                          <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/30">
                                              {k.category}
                                            </span>
                                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 border border-blue-500/30">
                                              CUSTOMER
                                            </span>
                                            <h5 className="text-xs font-bold text-foreground">{k.title}</h5>
                                          </div>
                                        </div>
                                        <p className="text-xs text-foreground/90 whitespace-pre-wrap">{k.content}</p>
                                        {(k.related_file_path || k.related_symbol) && (
                                          <div className="text-[11px] font-mono text-muted-foreground pt-1 border-t border-border flex items-center gap-3">
                                            {k.related_file_path && <span>File: {k.related_file_path}</span>}
                                            {k.related_symbol && <span>Symbol: {k.related_symbol}</span>}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ) : activeTab === 'overview' ? (
                      <div className="space-y-6">
                        {/* Repository context metadata */}
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            Indexed Repository State
                          </h4>
                          <div className="p-4 bg-muted/20 border border-border rounded-lg text-xs space-y-1.5">
                            <div><strong>Repository:</strong> {repo.full_name}</div>
                            <div><strong>URL:</strong> <a href={repo.url} target="_blank" rel="noreferrer" className="text-blue-600 underline">{repo.url}</a></div>
                            <div><strong>Commit SHA:</strong> {snapshot.commit_sha || 'Latest HEAD'}</div>
                            <div><strong>Parser Status:</strong> Completed AST indexing with zero unhandled crashes</div>
                          </div>
                        </div>

                        {/* Proactive Discoveries Summary Panel */}
                        <div className="border border-border rounded-xl bg-card p-5 shadow-xs space-y-4">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
                            <div className="flex items-center gap-2.5">
                              <div className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-900 flex items-center justify-center text-blue-600">
                                <Compass className="w-4 h-4" />
                              </div>
                              <div>
                                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                                  <span>Proactive Project Discoveries</span>
                                  <span className="text-[10px] font-mono font-normal px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                                    "I found something you should know"
                                  </span>
                                </h3>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                  Deterministic structural, dependency, and code quality analysis.
                                </p>
                              </div>
                            </div>

                            <button
                              onClick={handleTriggerDiscovery}
                              disabled={analyzing}
                              className="inline-flex items-center space-x-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors shadow-xs disabled:opacity-50"
                            >
                              <RotateCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                              <span>{analyzing ? 'Analyzing Project...' : 'Analyze Project'}</span>
                            </button>
                          </div>

                          {/* Severity breakdown counters */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            <div className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg">
                              <div className="flex items-center justify-between text-xs text-red-600 dark:text-red-400 font-semibold mb-1">
                                <span>Critical</span>
                                <ShieldAlert className="w-3.5 h-3.5" />
                              </div>
                              <span className="text-xl font-bold text-foreground">
                                {discoverSummary?.critical_count ?? 0}
                              </span>
                            </div>

                            <div className="p-3 bg-orange-500/5 border border-orange-500/20 rounded-lg">
                              <div className="flex items-center justify-between text-xs text-orange-600 dark:text-orange-400 font-semibold mb-1">
                                <span>High</span>
                                <AlertCircle className="w-3.5 h-3.5" />
                              </div>
                              <span className="text-xl font-bold text-foreground">
                                {discoverSummary?.high_count ?? 0}
                              </span>
                            </div>

                            <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                              <div className="flex items-center justify-between text-xs text-amber-600 dark:text-amber-400 font-semibold mb-1">
                                <span>Medium</span>
                                <Lightbulb className="w-3.5 h-3.5" />
                              </div>
                              <span className="text-xl font-bold text-foreground">
                                {discoverSummary?.medium_count ?? 0}
                              </span>
                            </div>

                            <div className="p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                              <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400 font-semibold mb-1">
                                <span>Low</span>
                                <CheckCircle2 className="w-3.5 h-3.5" />
                              </div>
                              <span className="text-xl font-bold text-foreground">
                                {discoverSummary?.low_count ?? 0}
                              </span>
                            </div>
                          </div>

                          {/* Top findings list preview */}
                          {findings.length > 0 ? (
                            <div className="space-y-2 pt-2">
                              <span className="text-xs font-semibold text-foreground">
                                Top Discoveries:
                              </span>
                              <div className="space-y-2">
                                {findings.slice(0, 3).map((f) => (
                                  <div
                                    key={f.id}
                                    className="p-3 border border-border rounded-lg bg-card hover:bg-muted/30 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                                  >
                                    <div className="space-y-1 max-w-2xl">
                                      <div className="flex items-center gap-2">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadgeClass(f.severity)}`}>
                                          {f.severity}
                                        </span>
                                        <span className="font-semibold text-foreground">{f.title}</span>
                                      </div>
                                      <p className="text-muted-foreground line-clamp-1">
                                        {f.why_it_matters || f.description}
                                      </p>
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                      <button
                                        onClick={() => handleInvestigateFinding(f)}
                                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:hover:bg-blue-900 dark:text-blue-300 rounded border border-blue-200 dark:border-blue-800 text-[11px] font-semibold transition-colors shadow-2xs"
                                      >
                                        <Sparkles className="w-3 h-3" />
                                        <span>Investigate</span>
                                      </button>
                                      <button
                                        onClick={() => setSelectedFinding(f)}
                                        className="inline-flex items-center space-x-1 px-2.5 py-1 bg-card hover:bg-muted text-muted-foreground hover:text-foreground rounded border border-border text-[11px] font-medium transition-colors"
                                      >
                                        <Eye className="w-3 h-3" />
                                        <span>Details</span>
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>

                              <div className="pt-2 flex justify-end">
                                <button
                                  onClick={() => {
                                    setActiveTab('discoveries');
                                    loadFindings();
                                  }}
                                  className="text-xs text-blue-600 dark:text-blue-400 font-semibold hover:underline inline-flex items-center gap-1"
                                >
                                  <span>View all {discoverSummary?.total_findings || findings.length} discoveries</span>
                                  <ArrowRight className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="py-6 text-center text-xs text-muted-foreground space-y-2">
                              <p>No project discoveries recorded yet.</p>
                              <p>Click "Analyze Project" to run automated deterministic AST and dependency discovery.</p>
                            </div>
                          )}
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
                    ) : activeTab === 'discoveries' ? (
                      <div className="space-y-6">
                        {/* Discoveries Header */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
                          <div>
                            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                              <Compass className="w-4 h-4 text-blue-600" />
                              <span>Project Discovery Engine</span>
                              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                                {discoverSummary?.total_findings ?? findings.length} findings
                              </span>
                            </h3>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Proactive structural risks, high-coupling hotspots, circular dependencies, documentation gaps, and legacy code.
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleTriggerDiscovery}
                              disabled={analyzing}
                              className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-1.5 transition-colors shadow-xs disabled:opacity-50"
                            >
                              <RotateCw className={`w-3.5 h-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                              <span>{analyzing ? 'Analyzing Repository...' : 'Run Discovery Analysis'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Analyzing banner */}
                        {analyzing && (
                          <div className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded-lg flex items-center gap-2.5 text-xs text-blue-700 dark:text-blue-300">
                            <RotateCw className="w-4 h-4 animate-spin text-blue-600" />
                            <span>
                              Discovery engine is running multi-analyzer pipeline (circular dependencies, coupling, doc gaps, duplication, architecture, test gaps)...
                            </span>
                          </div>
                        )}

                        {/* Filters & Search Toolbar */}
                        <div className="flex flex-wrap items-center gap-3 p-3 bg-muted/20 border border-border rounded-xl">
                          <div className="flex-1 min-w-[200px] relative">
                            <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5" />
                            <input
                              type="text"
                              value={searchQuery}
                              onChange={(e) => setSearchQuery(e.target.value)}
                              placeholder="Search findings by title, description, entity..."
                              className="w-full pl-8 pr-3 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          </div>

                          <div className="flex items-center gap-2 flex-wrap text-xs">
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <Filter className="w-3.5 h-3.5" />
                              <span>Status:</span>
                            </div>
                            <select
                              value={statusFilter}
                              onChange={(e) => setStatusFilter(e.target.value)}
                              className="px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none"
                            >
                              <option value="ALL">All Statuses</option>
                              <option value="OPEN">Open</option>
                              <option value="ACKNOWLEDGED">Acknowledged</option>
                              <option value="RESOLVED">Resolved</option>
                              <option value="DISMISSED">Dismissed</option>
                            </select>

                            <div className="flex items-center gap-1 text-muted-foreground ml-1">
                              <span>Severity:</span>
                            </div>
                            <select
                              value={severityFilter}
                              onChange={(e) => setSeverityFilter(e.target.value)}
                              className="px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none"
                            >
                              <option value="ALL">All Severities</option>
                              <option value="CRITICAL">Critical</option>
                              <option value="HIGH">High</option>
                              <option value="MEDIUM">Medium</option>
                              <option value="LOW">Low</option>
                            </select>

                            <div className="flex items-center gap-1 text-muted-foreground ml-1">
                              <span>Category:</span>
                            </div>
                            <select
                              value={categoryFilter}
                              onChange={(e) => setCategoryFilter(e.target.value)}
                              className="px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none"
                            >
                              <option value="ALL">All Categories</option>
                              <option value="CIRCULAR_DEPENDENCY">Circular Dependency</option>
                              <option value="COUPLING">High Coupling</option>
                              <option value="CHANGE_RISK">Change Risk</option>
                              <option value="UNUSED_CODE">Unused Code</option>
                              <option value="DOCUMENTATION_GAP">Documentation Gap</option>
                              <option value="DUPLICATION">Duplication</option>
                              <option value="ARCHITECTURE">Architecture</option>
                              <option value="LEGACY">Legacy Code</option>
                              <option value="TEST_GAP">Test Gap</option>
                            </select>
                          </div>
                        </div>

                        {/* Findings Grid / List */}
                        {loadingFindings ? (
                          <div className="py-16 text-center text-xs text-muted-foreground">
                            Loading project findings...
                          </div>
                        ) : filteredFindings.length === 0 ? (
                          <div className="py-16 text-center border border-border border-dashed rounded-xl bg-muted/10 space-y-2">
                            <Compass className="w-8 h-8 text-muted-foreground mx-auto stroke-1" />
                            <h4 className="text-sm font-semibold text-foreground">No matching findings found</h4>
                            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                              {searchQuery || statusFilter !== 'ALL' || severityFilter !== 'ALL' || categoryFilter !== 'ALL'
                                ? 'Try adjusting your search or filters.'
                                : 'Run discovery analysis to inspect this codebase for architectural risks.'}
                            </p>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 gap-3">
                            {filteredFindings.map((f) => (
                              <div
                                key={f.id}
                                className="border border-border rounded-xl bg-card p-4 hover:border-blue-500/40 transition-colors shadow-2xs space-y-3"
                              >
                                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                                  <div className="space-y-1.5">
                                    <div className="flex flex-wrap items-center gap-1.5">
                                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadgeClass(f.severity)}`}>
                                        {f.severity}
                                      </span>
                                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground border border-border">
                                        {f.category.replace(/_/g, ' ')}
                                      </span>
                                      <span className="px-2 py-0.5 rounded text-[10px] font-medium text-muted-foreground">
                                        Confidence: {f.confidence}
                                      </span>
                                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadgeClass(f.status)}`}>
                                        {f.status}
                                      </span>
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">{f.title}</h4>
                                  </div>

                                  {/* Action Buttons */}
                                  <div className="flex items-center gap-1.5 shrink-0 self-start">
                                    <button
                                      onClick={() => handleInvestigateFinding(f)}
                                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs"
                                    >
                                      <Sparkles className="w-3.5 h-3.5" />
                                      <span>Investigate</span>
                                    </button>
                                    <button
                                      onClick={() => setSelectedFinding(f)}
                                      className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-muted/60 hover:bg-muted text-foreground rounded-lg border border-border text-xs font-medium transition-colors"
                                    >
                                      <Eye className="w-3.5 h-3.5" />
                                      <span>Details</span>
                                    </button>
                                    <button
                                      onClick={() => openAddKnowledgeModal({
                                        findingId: f.id,
                                        filePath: f.evidence?.[0]?.file || (f.related_entities?.[0]?.includes('/') ? f.related_entities[0] : undefined),
                                        symbol: f.related_entities?.find((e: string) => !e.includes('/')),
                                        title: `${f.title} context`,
                                      })}
                                      className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-400 rounded-lg border border-amber-500/30 text-xs font-medium transition-colors"
                                      title="Add Project Knowledge"
                                    >
                                      <Brain className="w-3.5 h-3.5" />
                                      <span>Add Knowledge</span>
                                    </button>
                                  </div>
                                </div>

                                <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                                  {f.why_it_matters || f.description}
                                </p>

                                {/* Bottom Metadata & Quick Status Actions */}
                                <div className="pt-2 border-t border-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-muted-foreground">
                                  <div className="flex flex-wrap items-center gap-1.5">
                                    {f.evidence && f.evidence.length > 0 && (
                                      <span className="font-mono text-[11px] text-foreground font-semibold">
                                        {f.evidence.length} evidence {f.evidence.length === 1 ? 'item' : 'items'}
                                      </span>
                                    )}
                                    {f.related_entities && f.related_entities.slice(0, 3).map((e) => (
                                      <span
                                        key={e}
                                        className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-muted/80 text-foreground border border-border"
                                      >
                                        {e}
                                      </span>
                                    ))}
                                    {f.related_entities && f.related_entities.length > 3 && (
                                      <span className="text-[10px] text-muted-foreground font-mono">
                                        +{f.related_entities.length - 3} more
                                      </span>
                                    )}
                                  </div>

                                  <div className="flex items-center gap-1">
                                    <span className="text-[10px] mr-1 text-muted-foreground">Status:</span>
                                    {f.status === 'OPEN' && (
                                      <>
                                        <button
                                          onClick={() => handleUpdateFindingStatus(f.id, 'ACKNOWLEDGED')}
                                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-muted hover:bg-muted/80 text-foreground border border-border"
                                        >
                                          Acknowledge
                                        </button>
                                        <button
                                          onClick={() => handleUpdateFindingStatus(f.id, 'RESOLVED')}
                                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:hover:bg-emerald-900 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                                        >
                                          Resolve
                                        </button>
                                        <button
                                          onClick={() => handleUpdateFindingStatus(f.id, 'DISMISSED')}
                                          className="px-2 py-0.5 rounded text-[10px] font-medium text-muted-foreground hover:text-foreground"
                                        >
                                          Dismiss
                                        </button>
                                      </>
                                    )}
                                    {f.status === 'ACKNOWLEDGED' && (
                                      <>
                                        <button
                                          onClick={() => handleUpdateFindingStatus(f.id, 'RESOLVED')}
                                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:hover:bg-emerald-900 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                                        >
                                          Resolve
                                        </button>
                                        <button
                                          onClick={() => handleUpdateFindingStatus(f.id, 'DISMISSED')}
                                          className="px-2 py-0.5 rounded text-[10px] font-medium text-muted-foreground hover:text-foreground"
                                        >
                                          Dismiss
                                        </button>
                                      </>
                                    )}
                                    {(f.status === 'RESOLVED' || f.status === 'DISMISSED') && (
                                      <button
                                        onClick={() => handleUpdateFindingStatus(f.id, 'OPEN')}
                                        className="px-2 py-0.5 rounded text-[10px] font-medium bg-muted hover:bg-muted/80 text-foreground border border-border"
                                      >
                                        Reopen
                                      </button>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : activeTab === 'knowledge' ? (
                      <div className="space-y-6">
                        {/* Header Banner */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-bold text-foreground">PROJECT KNOWLEDGE</h3>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                                CUSTOMER-PROVIDED
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-1 max-w-2xl leading-relaxed">
                              Teach Unotusk domain facts, architectural decisions, business rules, exceptions, and legacy constraints.
                              Customer knowledge is prioritized as context in Grounded Ask, Discovery, and Reports without altering observed code facts.
                            </p>
                          </div>

                          <button
                            onClick={() => openAddKnowledgeModal()}
                            className="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-2xs shrink-0 self-start sm:self-auto"
                          >
                            <Plus className="w-4 h-4" />
                            <span>Add Project Knowledge</span>
                          </button>
                        </div>

                        {/* Search & Filters */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                          <div className="relative flex-1 max-w-sm">
                            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
                            <input
                              type="text"
                              placeholder="Search project knowledge..."
                              value={knowledgeSearchQuery}
                              onChange={(e) => setKnowledgeSearchQuery(e.target.value)}
                              className="w-full pl-9 pr-3 py-1.5 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <div className="flex flex-wrap items-center gap-2">
                            <div className="flex items-center gap-1 text-muted-foreground">
                              <span>Status:</span>
                            </div>
                            <select
                              value={knowledgeStatusFilter}
                              onChange={(e) => setKnowledgeStatusFilter(e.target.value)}
                              className="px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none"
                            >
                              <option value="ACTIVE">Active Only</option>
                              <option value="ARCHIVED">Archived</option>
                              <option value="ALL">All Statuses</option>
                            </select>

                            <div className="flex items-center gap-1 text-muted-foreground ml-1">
                              <span>Category:</span>
                            </div>
                            <select
                              value={knowledgeCategoryFilter}
                              onChange={(e) => setKnowledgeCategoryFilter(e.target.value)}
                              className="px-2.5 py-1.5 text-xs bg-background border border-border rounded-lg focus:outline-none"
                            >
                              <option value="ALL">All Categories</option>
                              <option value="INTENT">Intent</option>
                              <option value="BUSINESS_RULE">Business Rule</option>
                              <option value="ARCHITECTURE_DECISION">Architecture Decision</option>
                              <option value="EXCEPTION">Exception</option>
                              <option value="CONSTRAINT">Constraint</option>
                              <option value="LEGACY_CONTEXT">Legacy Context</option>
                              <option value="CRITICAL_COMPONENT">Critical Component</option>
                              <option value="TEMPORARY_STATE">Temporary State</option>
                              <option value="OTHER">Other</option>
                            </select>
                          </div>
                        </div>

                        {/* Knowledge List */}
                        {loadingKnowledge ? (
                          <div className="py-16 text-center text-xs text-muted-foreground">
                            Loading project knowledge...
                          </div>
                        ) : knowledgeList.length === 0 ? (
                          <div className="py-16 text-center border border-border border-dashed rounded-xl bg-muted/10 space-y-3">
                            <Brain className="w-10 h-10 text-muted-foreground mx-auto stroke-1" />
                            <div className="space-y-1">
                              <h4 className="text-sm font-semibold text-foreground">No project knowledge found</h4>
                              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                                {knowledgeSearchQuery || knowledgeStatusFilter !== 'ACTIVE' || knowledgeCategoryFilter !== 'ALL'
                                  ? 'No knowledge items match your search and filter criteria.'
                                  : 'Explicitly teach Unotusk about architecture decisions, business rules, or legacy context so future Ask and Reports incorporate your team\'s intent.'}
                              </p>
                            </div>
                            <button
                              onClick={() => openAddKnowledgeModal()}
                              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold"
                            >
                              <Plus className="w-3.5 h-3.5" />
                              <span>Add First Knowledge</span>
                            </button>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 gap-3.5">
                            {knowledgeList.map((item) => (
                              <div
                                key={item.id}
                                className={`border rounded-xl p-4 transition-colors shadow-2xs space-y-3 ${
                                  item.status === 'ARCHIVED'
                                    ? 'bg-muted/10 border-border/60 opacity-75'
                                    : 'bg-card border-border hover:border-amber-500/40'
                                }`}
                              >
                                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                                  <div className="space-y-1.5">
                                    <div className="flex flex-wrap items-center gap-1.5">
                                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                                        CUSTOMER
                                      </span>
                                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-muted text-muted-foreground border border-border">
                                        {item.category.replace(/_/g, ' ')}
                                      </span>
                                      <span
                                        className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                                          item.status === 'ACTIVE'
                                            ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                                            : 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/30'
                                        }`}
                                      >
                                        {item.status}
                                      </span>
                                      <span className="text-[10px] text-muted-foreground">
                                        Added {new Date(item.created_at).toLocaleDateString()}
                                      </span>
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">{item.title}</h4>
                                  </div>

                                  {/* Action Buttons */}
                                  <div className="flex items-center gap-1.5 shrink-0 self-start">
                                    <button
                                      onClick={() => openEditKnowledgeModal(item)}
                                      className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-muted/60 hover:bg-muted text-foreground rounded-lg border border-border text-xs font-medium transition-colors"
                                    >
                                      <span>Edit</span>
                                    </button>
                                    {item.status === 'ACTIVE' ? (
                                      <button
                                        onClick={() => handleArchiveKnowledge(item.id)}
                                        className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg border border-border text-xs font-medium transition-colors"
                                      >
                                        <span>Archive</span>
                                      </button>
                                    ) : (
                                      <button
                                        onClick={() => handleRestoreKnowledge(item.id)}
                                        className="inline-flex items-center space-x-1 px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 rounded-lg border border-emerald-200 dark:border-emerald-800 text-xs font-medium transition-colors"
                                      >
                                        <span>Restore</span>
                                      </button>
                                    )}
                                  </div>
                                </div>

                                <p className="text-xs text-foreground/90 whitespace-pre-wrap leading-relaxed">
                                  {item.content}
                                </p>

                                {/* Related entity references */}
                                {(item.related_file_path || item.related_symbol || item.related_finding_id) && (
                                  <div className="pt-2 border-t border-border flex flex-wrap items-center gap-2 text-xs">
                                    <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">
                                      Related:
                                    </span>
                                    {item.related_file_path && (
                                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-muted/60 text-foreground border border-border">
                                        file: {item.related_file_path}
                                      </span>
                                    )}
                                    {item.related_symbol && (
                                      <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-900 font-bold">
                                        symbol: {item.related_symbol}
                                      </span>
                                    )}
                                    {item.related_finding_id && (
                                      <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-900">
                                        finding: {item.related_finding_id.slice(0, 8)}...
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>
                            ))}
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

      {/* Slide-over Finding Detail Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-5 border-b border-border flex items-start justify-between gap-4 bg-muted/20">
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadgeClass(selectedFinding.severity)}`}>
                    {selectedFinding.severity}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground border border-border">
                    {selectedFinding.category.replace(/_/g, ' ')}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getStatusBadgeClass(selectedFinding.status)}`}>
                    {selectedFinding.status}
                  </span>
                  <span className="text-[10px] text-muted-foreground">
                    Confidence: {selectedFinding.confidence}
                  </span>
                </div>
                <h3 className="text-base font-bold text-foreground">
                  {selectedFinding.title}
                </h3>
              </div>
              <button
                onClick={() => setSelectedFinding(null)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Scrollable Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs">
              {/* WHAT WE FOUND */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
                  What We Found
                </h4>
                <p className="text-foreground leading-relaxed">
                  {selectedFinding.description}
                </p>
              </div>

              {/* WHY IT MATTERS */}
              <div className="space-y-1.5 p-3.5 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                <h4 className="font-bold text-[11px] uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  Why It Matters
                </h4>
                <p className="text-foreground leading-relaxed">
                  {selectedFinding.why_it_matters}
                </p>
              </div>

              {/* RECOMMENDATION */}
              <div className="space-y-1.5 p-3.5 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                <h4 className="font-bold text-[11px] uppercase tracking-wider text-blue-600 dark:text-blue-400">
                  Recommendation
                </h4>
                <p className="text-foreground leading-relaxed">
                  {selectedFinding.recommendation}
                </p>
              </div>

              {/* EVIDENCE */}
              {selectedFinding.evidence && selectedFinding.evidence.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
                    Evidence ({selectedFinding.evidence.length})
                  </h4>
                  <div className="space-y-2.5">
                    {selectedFinding.evidence.map((ev, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-muted/20 border border-border rounded-lg space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                          <span className="font-mono font-semibold text-foreground">
                            {ev.file || 'File'} {ev.lines ? `:${ev.lines}` : ''}
                          </span>
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                            Type: {ev.type}
                          </span>
                        </div>
                        {ev.consumers_count !== undefined && (
                          <div className="text-[11px] text-muted-foreground font-mono">
                            Dependents / Consumers: {ev.consumers_count}
                          </div>
                        )}
                        {ev.snippet && (
                          <pre className="p-2.5 bg-zinc-950 text-zinc-200 rounded text-[11px] font-mono overflow-x-auto whitespace-pre-wrap leading-relaxed">
                            {ev.snippet}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* RELATED ENTITIES */}
              {selectedFinding.related_entities && selectedFinding.related_entities.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-bold text-[11px] uppercase tracking-wider text-muted-foreground">
                    Related Entities
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedFinding.related_entities.map((ent) => (
                      <span
                        key={ent}
                        className="px-2 py-0.5 bg-muted rounded text-[11px] font-mono text-foreground border border-border"
                      >
                        {ent}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border bg-muted/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-1.5">
                {selectedFinding.status !== 'ACKNOWLEDGED' && selectedFinding.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleUpdateFindingStatus(selectedFinding.id, 'ACKNOWLEDGED')}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-card hover:bg-muted text-foreground border border-border transition-colors"
                  >
                    Acknowledge
                  </button>
                )}
                {selectedFinding.status !== 'RESOLVED' && (
                  <button
                    onClick={() => handleUpdateFindingStatus(selectedFinding.id, 'RESOLVED')}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:hover:bg-emerald-900 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 transition-colors"
                  >
                    Mark Resolved
                  </button>
                )}
                {selectedFinding.status !== 'DISMISSED' && (
                  <button
                    onClick={() => handleUpdateFindingStatus(selectedFinding.id, 'DISMISSED')}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Dismiss
                  </button>
                )}
                {(selectedFinding.status === 'RESOLVED' || selectedFinding.status === 'DISMISSED') && (
                  <button
                    onClick={() => handleUpdateFindingStatus(selectedFinding.id, 'OPEN')}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-card hover:bg-muted text-foreground border border-border transition-colors"
                  >
                    Reopen
                  </button>
                )}
                <button
                  onClick={() => {
                    const f = selectedFinding;
                    openAddKnowledgeModal({
                      findingId: f.id,
                      filePath: f.evidence?.[0]?.file || (f.related_entities?.[0]?.includes('/') ? f.related_entities[0] : undefined),
                      symbol: f.related_entities?.find((e: string) => !e.includes('/')),
                      title: `${f.title} context`,
                    });
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 hover:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30 transition-colors flex items-center gap-1.5"
                >
                  <Brain className="w-3.5 h-3.5" />
                  <span>Add Project Knowledge</span>
                </button>
              </div>

              <button
                onClick={() => handleInvestigateFinding(selectedFinding)}
                className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
              >
                <Sparkles className="w-4 h-4" />
                <span>Investigate with Grounded Ask</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Inspection Modal */}
      {inspectedEvidence && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <Eye className="w-4 h-4 text-blue-600" />
                  <span>{inspectedEvidence.title}</span>
                </h3>
                {inspectedEvidence.statement && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {inspectedEvidence.statement}
                  </p>
                )}
              </div>
              <button
                onClick={() => setInspectedEvidence(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-muted"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3 flex-1">
              {inspectedEvidence.evidence && inspectedEvidence.evidence.length > 0 ? (
                inspectedEvidence.evidence.map((ev: any, idx: number) => (
                  <div key={idx} className="p-3 bg-muted/20 border border-border rounded-lg text-xs space-y-1.5">
                    <div className="flex items-center justify-between font-mono text-[11px]">
                      <span className="text-foreground font-semibold">
                        {ev.file_path || ev.file || ev.target || 'Repository Entity'}
                      </span>
                      {ev.reference_type && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 font-sans uppercase">
                          {ev.reference_type}
                        </span>
                      )}
                    </div>
                    {(ev.symbol || ev.source_symbol) && (
                      <div className="text-muted-foreground">
                        Symbol: <code className="text-[11px] font-mono font-bold text-foreground">{ev.symbol || ev.source_symbol}</code>
                      </div>
                    )}
                    {(ev.line_number || (ev.start_line && ev.end_line)) && (
                      <div className="text-muted-foreground font-mono text-[10px]">
                        Line: {ev.line_number ? `L${ev.line_number}` : `L${ev.start_line} - L${ev.end_line}`}
                      </div>
                    )}
                    {ev.snippet && (
                      <pre className="p-2.5 bg-background border border-border rounded text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap">
                        {ev.snippet}
                      </pre>
                    )}
                  </div>
                ))
              ) : (
                <div className="py-6 text-center text-xs text-muted-foreground">
                  No detailed line snippets available for this evidence item.
                </div>
              )}
            </div>

            <div className="p-3 border-t border-border bg-muted/20 flex justify-end">
              <button
                onClick={() => setInspectedEvidence(null)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-muted hover:bg-muted/80 text-foreground border border-border"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / Edit Project Knowledge Modal */}
      {showKnowledgeModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-base font-bold text-foreground">
                  {editingKnowledgeId ? 'Edit Project Knowledge' : 'Add Project Knowledge'}
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Teach Unotusk explicit domain decisions, intent, constraints, or exceptions.
                </p>
              </div>
              <button
                onClick={() => setShowKnowledgeModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {knowledgeError && (
              <div className="p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900 rounded-lg text-xs text-red-600 dark:text-red-400">
                {knowledgeError}
              </div>
            )}

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold mb-1 text-foreground">Category</label>
                <select
                  value={knowledgeFormCategory}
                  onChange={(e) => setKnowledgeFormCategory(e.target.value as KnowledgeCategory)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="ARCHITECTURE_DECISION">Architecture Decision</option>
                  <option value="INTENT">Intent</option>
                  <option value="BUSINESS_RULE">Business Rule</option>
                  <option value="EXCEPTION">Exception</option>
                  <option value="CONSTRAINT">Constraint</option>
                  <option value="LEGACY_CONTEXT">Legacy Context</option>
                  <option value="CRITICAL_COMPONENT">Critical Component</option>
                  <option value="TEMPORARY_STATE">Temporary State</option>
                  <option value="OTHER">Other</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1 text-foreground">Title</label>
                <input
                  type="text"
                  placeholder="e.g., AuthService centralization is intentional"
                  value={knowledgeFormTitle}
                  onChange={(e) => setKnowledgeFormTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="block font-semibold mb-1 text-foreground">
                  What should Unotusk remember about this project?
                </label>
                <textarea
                  rows={4}
                  placeholder="e.g., AuthService is the intentional boundary for authentication and session management. It should not be split even though it has high coupling."
                  value={knowledgeFormContent}
                  onChange={(e) => setKnowledgeFormContent(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block font-semibold mb-1 text-muted-foreground text-[11px]">
                    Related File (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="src/auth/service.py"
                    value={knowledgeFormFilePath}
                    onChange={(e) => setKnowledgeFormFilePath(e.target.value)}
                    className="w-full px-2.5 py-1.5 font-mono text-[11px] bg-background border border-border rounded-lg focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold mb-1 text-muted-foreground text-[11px]">
                    Related Symbol (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="AuthService"
                    value={knowledgeFormSymbol}
                    onChange={(e) => setKnowledgeFormSymbol(e.target.value)}
                    className="w-full px-2.5 py-1.5 font-mono text-[11px] bg-background border border-border rounded-lg focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-border">
              <button
                type="button"
                onClick={() => setShowKnowledgeModal(false)}
                className="px-3.5 py-2 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveKnowledge}
                disabled={savingKnowledge}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
              >
                {savingKnowledge ? 'Saving...' : 'Save Knowledge'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
