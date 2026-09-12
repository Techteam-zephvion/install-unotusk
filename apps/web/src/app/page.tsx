'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('unotusk_token') : null;
    if (token) {
      router.replace('/projects');
    } else {
      router.replace('/login');
    }
  }, [router]);

  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="text-sm text-muted-foreground animate-pulse">Loading Unotusk...</div>
    </div>
  );
}
