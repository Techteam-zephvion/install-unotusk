'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { api, getActiveOrg } from '@/lib/api';
import { Navbar } from '@/components/Navbar';
import { Organization, User } from '@unotusk/types';

export default function CreateProjectPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrgId, setActiveOrgId] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const me = await api.auth.me();
        setUser(me.user);
        setOrganizations(me.organizations);
        const savedOrg = getActiveOrg();
        if (savedOrg && me.organizations.some((o) => o.id === savedOrg)) {
          setActiveOrgId(savedOrg);
        } else if (me.organizations.length > 0) {
          setActiveOrgId(me.organizations[0].id);
        }
      } catch {
        router.push('/login');
      }
    }
    loadData();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrgId) {
      setError('Please select an organization');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const project = await api.projects.create({
        organization_id: activeOrgId,
        name: name.trim(),
        description: description.trim() || undefined,
      });

      // Redirect immediately to Project Overview
      router.push(`/projects/${project.id}`);
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar
        organizations={organizations}
        activeOrgId={activeOrgId || undefined}
        onSelectOrg={(id) => setActiveOrgId(id)}
        userEmail={user?.email}
      />

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-8">
        <Link
          href="/projects"
          className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to projects</span>
        </Link>

        <div className="bg-card border border-border rounded-xl p-6 sm:p-8 shadow-sm">
          <h1 className="text-xl font-bold tracking-tight">Create New Project</h1>
          <p className="text-xs text-muted-foreground mt-1 mb-6">
            Establish a dedicated boundary for this project within your organization.
          </p>

          {error && (
            <div className="mb-6 p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg text-xs text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold mb-1.5" htmlFor="org-select">
                Organization
              </label>
              <select
                id="org-select"
                value={activeOrgId || ''}
                onChange={(e) => setActiveOrgId(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" htmlFor="name">
                Project Name
              </label>
              <input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Core Commerce Engine"
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5" htmlFor="description">
                Description <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <textarea
                id="description"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of the project codebase and domain..."
                className="w-full px-3 py-2 text-sm bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="pt-2 flex items-center justify-end space-x-3">
              <Link
                href="/projects"
                className="px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg transition-colors"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
