import React from "react";
import { Link } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-600 text-white shadow-soft">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold tracking-tight">Schlagwortsuche</h1>
          <div className="flex items-center gap-4 text-sm opacity-90">
            <span>FAISS · FastAPI</span>
            {/* Admin-Link */}
            <Link
              to="/admin"
              className="underline hover:text-white transition"
            >
              Admin
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-5xl mx-auto px-4 py-6">{children}</div>
      </main>

      <footer className="bg-white/70 backdrop-blur border-t">
        <div className="max-w-5xl mx-auto px-4 py-3 text-xs text-slate-500 flex items-center gap-2">
          <span>© {new Date().getFullYear()} – Suche</span>
          <span>•</span>
          <span>React + Tailwind</span>
        </div>
      </footer>
    </div>
  );
}
