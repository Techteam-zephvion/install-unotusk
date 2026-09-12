'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus, FolderKanban, Calendar, ArrowRight, ShieldCheck } from 'lucide-react';
import { api, getActiveOrg, setActiveOrg } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { Organization, Project, User } from '@unotusk/types';

export default function ProjectsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load user & organizations
  useEffect(() => {
    async function loadInitialData() {
      try {
        setLoading(true);
        const me = await api.auth.me();
        setUser(me.user);
        setOrganizations(me.organizations);

        let selectedOrgId = getActiveOrg();
        const orgExists = me.organizations.some((o) => o.id === selectedOrgId);
        if (!orgExists && me.organizations.length > 0) {
          selectedOrgId = me.organizations[0].id;
          setActiveOrg(selectedOrgId);
        }
        setActiveOrgIdState(selectedOrgId);

        if (selectedOrgId) {
          const projs = await api.projects.list(selectedOrgId);
          setProjects(projs);
        }
      } catch (err: any) {
        if (err.status === 401) {
          router.push('/login');
          return;
        }
        setError(err.message || 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    }

    loadInitialData();
  }, [router]);

  const handleOrgChange = async (orgId: string) => {
    setActiveOrg(orgId);
    setActiveOrgIdState(orgId);
    setLoading(true);
    setError(null);
    try {
      const projs = await api.projects.list(orgId);
      setProjects(projs);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects for organization');
    } finally {
      setLoading(false);
    }
  };

  const activeOrg = organizations.find((o) => o.id === activeOrgId);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar
        organizations={organizations}
        activeOrgId={activeOrgId || undefined}
        onSelectOrg={handleOrgChange}
        userEmail={user?.email}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Projects</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Organization:{' '}
              <span className="font-medium text-foreground">
                {activeOrg?.name || 'No organization selected'}
              </span>
            </p>
          </div>

          <Link
            href="/projects/new"
            className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Create Project</span>
          </Link>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-16 px-4 border border-dashed border-border rounded-xl bg-card">
            <FolderKanban className="w-12 h-12 mx-auto text-muted-foreground stroke-1 mb-3" />
            <h2 className="text-base font-semibold">No projects yet</h2>
            <p className="text-xs text-muted-foreground max-w-md mx-auto mt-1 mb-6">
              Create your first project to establish the project boundary and prepare for repository connection in Stage 1.
            </p>
            <Link
              href="/projects/new"
              className="inline-flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Create First Project</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((project) => (
              <div
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}`)}
                className="bg-card border border-border hover:border-blue-500/50 rounded-xl p-5 shadow-sm hover:shadow transition cursor-pointer flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                      {project.status}
                    </span>
                    <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <h2 className="text-base font-bold text-foreground group-hover:text-blue-600 transition-colors line-clamp-1">
                    {project.name}
                  </h2>
                  <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">
                    {project.description || 'No description provided.'}
                  </p>
                </div>

                <div className="mt-6 pt-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                  <span className="font-mono text-[11px]">{project.slug}</span>
                  <span className="inline-flex items-center gap-1 text-blue-600 font-medium group-hover:translate-x-0.5 transition-transform">
                    Overview <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
