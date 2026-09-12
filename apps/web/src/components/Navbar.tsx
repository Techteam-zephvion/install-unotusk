'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, Layers } from 'lucide-react';
import { removeToken } from '@/lib/api';
import { Organization } from '@unotusk/types';

interface NavbarProps {
  organizations?: Organization[];
  activeOrgId?: string;
  onSelectOrg?: (orgId: string) => void;
  userEmail?: string;
}

export function Navbar({
  organizations = [],
  activeOrgId,
  onSelectOrg,
  userEmail,
}: NavbarProps) {
  const router = useRouter();

  const handleLogout = () => {
    removeToken();
    router.push('/login');
  };

  return (
    <header className="border-b border-border bg-card/60 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <div
            onClick={() => router.push('/projects')}
            className="flex items-center space-x-2 font-bold text-lg cursor-pointer tracking-tight"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-sm">
              U
            </div>
            <span>Unotusk</span>
          </div>

          {organizations.length > 0 && (
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-muted-foreground" />
              <select
                value={activeOrgId || ''}
                onChange={(e) => onSelectOrg && onSelectOrg(e.target.value)}
                aria-label="Select active organization"
                className="bg-transparent text-sm font-medium border border-border rounded-md px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-4">
          {userEmail && (
            <span className="text-xs text-muted-foreground hidden sm:inline-block">
              {userEmail}
            </span>
          )}
          <button
            onClick={handleLogout}
            className="inline-flex items-center space-x-1.5 text-xs text-muted-foreground hover:text-foreground px-2.5 py-1.5 rounded-md hover:bg-muted transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </header>
  );
}
