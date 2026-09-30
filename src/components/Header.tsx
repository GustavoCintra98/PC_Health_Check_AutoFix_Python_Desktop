import React from 'react';
import { Shield, ShieldAlert, Zap, Search, FileText } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isAdmin: boolean;
  onToggleAdmin: () => void;
  onRunDiagnosis: () => void;
  onRunAutoFix: () => void;
  onOpenReport: () => void;
  isDiagnosing: boolean;
  isFixing: boolean;
  unresolvedCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  isAdmin,
  onToggleAdmin,
  onRunDiagnosis,
  onRunAutoFix,
  onOpenReport,
  isDiagnosing,
  isFixing,
  unresolvedCount
}) => {
  const navTabs = [
    { id: 'dashboard', label: 'Painel Geral' },
    { id: 'processes', label: 'Processos & CPU' },
    { id: 'storage', label: 'Disco & Limpeza' },
    { id: 'network', label: 'Rede & Conectividade' },
    { id: 'os_services', label: 'Integridade SO & Serviços' },
    { id: 'python_code', label: 'Código Python (Desktop)' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Zone 1: Single text element wordmark */}
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setActiveTab('dashboard')} 
            className="flex items-center gap-2.5 text-left transition-opacity hover:opacity-90"
          >
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-400">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white block">
                PC Health Check & Auto-Fix
              </span>
              <span className="text-[11px] text-slate-400 font-mono tracking-tight block">
                Windows System Diagnostics & Resolution
              </span>
            </div>
          </button>
        </div>

        {/* Zone 2: Navigation Links (Single line, text based, unboxed) */}
        <nav className="hidden lg:flex items-center gap-6">
          {navTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`text-sm font-medium transition-colors whitespace-nowrap py-1 relative ${
                  isActive 
                    ? 'text-cyan-400' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400 rounded-full" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: Primary Actions (UAC Toggle + Action Buttons) */}
        <div className="flex items-center gap-2.5">
          {/* UAC Elevation Status Button */}
          <button
            onClick={onToggleAdmin}
            title={isAdmin ? "Executando como Administrador (UAC Ativo)" : "Clique para solicitar elevação de Administrador"}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-mono transition-colors border ${
              isAdmin
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/30'
                : 'bg-amber-950/40 border-amber-500/30 text-amber-400 hover:bg-amber-900/30'
            }`}
          >
            {isAdmin ? <Shield className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{isAdmin ? 'UAC: Admin (Elevado)' : 'UAC: Padrão'}</span>
          </button>

          {/* Report Button */}
          <button
            onClick={onOpenReport}
            title="Exportar Relatório de Diagnóstico"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-900 border border-slate-700/60 rounded-md hover:bg-slate-800 hover:text-white transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-slate-400" />
            <span>Relatório</span>
          </button>

          {/* Phase 1: Diagnose */}
          <button
            onClick={onRunDiagnosis}
            disabled={isDiagnosing || isFixing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-800 border border-slate-700 rounded-md hover:bg-slate-700 hover:border-slate-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Search className={`h-3.5 w-3.5 ${isDiagnosing ? 'animate-spin' : 'text-cyan-400'}`} />
            <span>{isDiagnosing ? 'Analisando...' : 'Fase 1 (Diagnóstico)'}</span>
          </button>

          {/* Phase 2: Auto-Fix */}
          <button
            onClick={onRunAutoFix}
            disabled={isFixing || isDiagnosing}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-md shadow-sm shadow-cyan-950 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Zap className={`h-3.5 w-3.5 ${isFixing ? 'animate-bounce' : ''}`} />
            <span>{isFixing ? 'Reparando...' : 'Fase 2 (Auto-Fix)'}</span>
            {unresolvedCount > 0 && !isFixing && (
              <span className="ml-0.5 rounded bg-cyan-950 px-1.5 py-0.2 text-[10px] font-mono text-cyan-200">
                {unresolvedCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Mobile navigation tab scroll bar */}
      <div className="lg:hidden flex items-center gap-4 overflow-x-auto px-4 py-2 border-t border-slate-800/80 bg-slate-950/60 text-xs font-medium">
        {navTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap pb-1 border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-cyan-400 text-cyan-400 font-semibold'
                : 'border-transparent text-slate-400'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </header>
  );
};
