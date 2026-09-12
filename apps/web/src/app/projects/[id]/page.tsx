'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Calendar,
  Layers,
  GitBranch,
  ShieldAlert,
  Info,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { Organization, Project, User } from '@unotusk/types';

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const me = await api.auth.me();
        setUser(me.user);
        setOrganizations(me.organizations);

        const p = await api.projects.get(projectId);
        setProject(p);
      } catch (err: any) {
        if (err.status === 401) {
          router.push('/login');
          return;
        }
        setError(err.message || 'Failed to load project details');
      } finally {
        setLoading(false);
      }
    }

    if (projectId) {
      loadData();
    }
  }, [projectId, router]);

  const org = organizations.find((o) => o.id === project?.organization_id);

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
            Loading project overview...
          </div>
        ) : !project ? (
          <div className="text-center py-16">
            <h2 className="text-base font-semibold">Project not found</h2>
            <p className="text-xs text-muted-foreground mt-1">
              This project does not exist or you lack permission to view it.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
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

            {/* Stage 1 Repository Connection Entry Point */}
            <div className="border border-border rounded-xl bg-card p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center text-foreground">
                    <GitBranch className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-foreground">
                      Repository Connection
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      Stage 1 Integration Entry Point
                    </p>
                  </div>
                </div>

                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-900">
                  Ready for Stage 1
                </span>
              </div>

              <div className="p-4 bg-muted/40 border border-border rounded-lg text-xs space-y-2">
                <div className="flex items-center gap-2 text-foreground font-semibold">
                  <Info className="w-4 h-4 text-blue-600" />
                  <span>Stage 0 Boundary Established</span>
                </div>
                <p className="text-muted-foreground">
                  The project entity and integration record have been registered in the database.
                  Actual GitHub repository connection, webhooks, and commit ingestion will be activated in{' '}
                  <span className="font-semibold text-foreground">Stage 1: Project + GitHub Ingestion</span>.
                </p>
              </div>

              <div className="mt-5 flex items-center justify-between pt-4 border-t border-border">
                <div className="text-[11px] text-muted-foreground">
                  Integration status:{' '}
                  <span className="font-mono text-foreground font-medium">PENDING</span>
                </div>
                <button
                  disabled
                  className="inline-flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 bg-muted text-muted-foreground rounded-lg cursor-not-allowed border border-border"
                >
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>Connect Repository (Stage 1)</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
