import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Unotusk — Project Intelligence',
  description: 'Clean-slate foundation for Unotusk Project Intelligence MVP',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-background text-foreground flex flex-col">
        {children}
      </body>
    </html>
  );
}
