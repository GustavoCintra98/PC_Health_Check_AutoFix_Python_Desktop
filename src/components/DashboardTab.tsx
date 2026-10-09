import React from 'react';
import { 
  Activity, 
  HardDrive, 
  Wifi, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  Terminal, 
  Trash2, 
  RefreshCw,
  Cpu,
  ArrowRight,
  Server
} from 'lucide-react';
import { SystemHealthState } from '../types/system';

interface DashboardTabProps {
  systemState: SystemHealthState;
  onRunDiagnosis: () => void;
  onRunAutoFix: () => void;
  onNavigateTab: (tabId: string) => void;
  onClearLogs: () => void;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  systemState,
  onRunDiagnosis,
  onRunAutoFix,
  onNavigateTab,
  onClearLogs,
}) => {
  // Compute health score (0 - 100)
  const calculateScore = () => {
    let score = 100;
    if (systemState.cpuUsage > 75) score -= 15;
    if (systemState.ramUsagePercent > 80) score -= 15;
    if (systemState.sfcStatus === 'corrupted') score -= 25;
    if (systemState.network.packetLoss > 2) score -= 15;
    const stoppedCritical = systemState.services.filter(s => s.critical && s.status === 'Stopped').length;
    score -= stoppedCritical * 10;
    const totalTemp = systemState.storageCategories.reduce((acc, c) => !c.isCleaned ? acc + c.sizeMb : acc, 0);
    if (totalTemp > 1000) score -= 10;
    return Math.max(15, Math.min(100, score));
  };

  const healthScore = calculateScore();

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-emerald-400 border-emerald-500/30 bg-emerald-950/20';
    if (score >= 60) return 'text-amber-400 border-amber-500/30 bg-amber-950/20';
    return 'text-rose-400 border-rose-500/30 bg-rose-950/20';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 85) return 'Excelente (Estável & Otimizado)';
    if (score >= 60) return 'Atenção (Gargalos & Lixo Acumulado)';
    return 'Crítico (Violações de SO e Serviços Parados)';
  };

  const totalTempMb = systemState.storageCategories.reduce(
    (acc, curr) => !curr.isCleaned ? acc + curr.sizeMb : acc, 0
  );

  const topUserProcess = systemState.processes
    .filter(p => !p.isCritical && p.status === 'running')
    .sort((a, b) => b.cpu - a.cpu)[0];

  const stoppedCriticalServices = systemState.services.filter(
    s => s.critical && s.status === 'Stopped'
  );

  return (
    <div className="space-y-6">
      {/* Top Banner: Health Status & Fast Triggers */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex items-center gap-5">
            {/* Score Ring / Badge */}
            <div className={`flex h-20 w-20 shrink-0 flex-col items-center justify-center rounded-2xl border font-mono ${getScoreColor(healthScore)}`}>
              <span className="text-2xl font-bold tracking-tight">{healthScore}%</span>
              <span className="text-[10px] tracking-widest uppercase opacity-80">Saúde</span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Diagnóstico Geral do Sistema
                </h1>
                <span className="text-xs text-slate-400 font-mono">
                  {systemState.lastDiagnosisTime ? `Última varredura: ${systemState.lastDiagnosisTime}` : 'Pronto para análise'}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-300">
                Estado atual: <span className="font-semibold text-slate-100">{getScoreLabel(healthScore)}</span>.
                {' '}{systemState.detectedIssues.length} alertas pendentes identificados.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400 font-mono">
                <span>Windows 11 Pro 64-bit</span>
                <span>·</span>
                <span>UAC: {systemState.isAdmin ? 'Administrador' : 'Restrito'}</span>
                <span>·</span>
                <span>{systemState.cpuCores} Núcleos / {systemState.cpuThreads} Threads</span>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onRunDiagnosis}
              disabled={systemState.isDiagnosing || systemState.isFixing}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${systemState.isDiagnosing ? 'animate-spin text-cyan-400' : ''}`} />
              <span>{systemState.isDiagnosing ? 'Executando Varredura...' : 'Fase 1: Nova Análise Completa'}</span>
            </button>

            <button
              onClick={onRunAutoFix}
              disabled={systemState.isFixing || systemState.isDiagnosing}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 shadow-md shadow-cyan-950 transition-colors disabled:opacity-50"
            >
              <Activity className={`h-4 w-4 ${systemState.isFixing ? 'animate-bounce' : ''}`} />
              <span>{systemState.isFixing ? 'Executando Correções...' : 'Fase 2: Corrigir Problemas Detectados'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 High-Density Hardware & OS Diagnostic Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: CPU & RAM */}
        <div 
          onClick={() => onNavigateTab('processes')}
          className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 hover:bg-slate-900/60 transition-all cursor-pointer relative"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Processamento & RAM</span>
            <Cpu className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between font-mono">
            <span className="text-2xl font-bold text-white tabular-nums">{systemState.cpuUsage.toFixed(1)}%</span>
            <span className="text-xs text-slate-400">RAM: {systemState.ramUsagePercent.toFixed(0)}%</span>
          </div>
          <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${systemState.cpuUsage > 80 ? 'bg-rose-500' : systemState.cpuUsage > 50 ? 'bg-amber-400' : 'bg-cyan-400'}`}
              style={{ width: `${Math.min(100, systemState.cpuUsage)}%` }}
            />
          </div>
          <div className="mt-3 text-xs text-slate-400 truncate">
            {topUserProcess ? (
              <span>Gargalo: <strong className="text-slate-200">{topUserProcess.name}</strong> ({topUserProcess.cpu}%)</span>
            ) : (
              <span>Sem gargalo de usuário ativo</span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity">
            <span>Gerenciar processos</span>
            <ArrowRight className="h-3 w-3" />
          </div>
        </div>

        {/* Card 2: Armazenamento & Temp */}
        <div 
          onClick={() => onNavigateTab('storage')}
          className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 hover:bg-slate-900/60 transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Disco & Temporários</span>
            <HardDrive className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between font-mono">
            <span className="text-2xl font-bold text-white tabular-nums">
              {(totalTempMb / 1024).toFixed(1)} <span className="text-sm font-normal text-slate-400">GB</span>
            </span>
            <span className="text-xs text-slate-400">C: {systemState.drives[0]?.freeGb}GB livres</span>
          </div>
          <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${totalTempMb > 2000 ? 'bg-amber-500' : 'bg-indigo-400'}`}
              style={{ width: `${Math.min(100, (totalTempMb / 8000) * 100)}%` }}
            />
          </div>
          <div className="mt-3 text-xs text-slate-400 truncate">
            <span>S.M.A.R.T.: <strong className="text-emerald-400">Saudável (0 setores)</strong></span>
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
            <span>Limpar armazenamento</span>
            <ArrowRight className="h-3 w-3" />
          </div>
        </div>

        {/* Card 3: Rede & Latência */}
        <div 
          onClick={() => onNavigateTab('network')}
          className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 hover:bg-slate-900/60 transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Rede (Ping 8.8.8.8)</span>
            <Wifi className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between font-mono">
            <span className="text-2xl font-bold text-white tabular-nums">
              {systemState.network.pingMs} <span className="text-sm font-normal text-slate-400">ms</span>
            </span>
            <span className={`text-xs ${systemState.network.packetLoss > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              Perda: {systemState.network.packetLoss}%
            </span>
          </div>
          <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${systemState.network.pingMs > 80 ? 'bg-amber-500' : 'bg-emerald-400'}`}
              style={{ width: `${Math.min(100, (systemState.network.pingMs / 200) * 100)}%` }}
            />
          </div>
          <div className="mt-3 text-xs text-slate-400 truncate">
            <span>Adaptador: <strong className="text-slate-200">Intel 2.5GbE (Online)</strong></span>
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity">
            <span>Ver adaptadores & DNS</span>
            <ArrowRight className="h-3 w-3" />
          </div>
        </div>

        {/* Card 4: SO & Serviços */}
        <div 
          onClick={() => onNavigateTab('os_services')}
          className="group rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 hover:bg-slate-900/60 transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Integridade SO & Serviços</span>
            <ShieldCheck className="h-4 w-4 text-purple-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between font-mono">
            <span className="text-2xl font-bold text-white">
              {systemState.sfcStatus === 'corrupted' ? (
                <span className="text-rose-400">Violação</span>
              ) : (
                <span className="text-emerald-400">Íntegro</span>
              )}
            </span>
            <span className="text-xs text-slate-400">
              {stoppedCriticalServices.length} srv parados
            </span>
          </div>
          <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${systemState.sfcStatus === 'corrupted' ? 'bg-rose-500' : 'bg-emerald-400'}`}
              style={{ width: systemState.sfcStatus === 'corrupted' ? '85%' : '100%' }}
            />
          </div>
          <div className="mt-3 text-xs text-slate-400 truncate">
            {stoppedCriticalServices.length > 0 ? (
              <span className="text-amber-300">Parado: {stoppedCriticalServices[0].displayName}</span>
            ) : (
              <span className="text-emerald-400">Todos os serviços essenciais ativos</span>
            )}
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity">
            <span>Reparar SFC / Serviços</span>
            <ArrowRight className="h-3 w-3" />
          </div>
        </div>
      </div>

      {/* Discovered Issues vs Fixed Issues Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issues List Column */}
        <div className="lg:col-span-1 rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              <span>Problemas Detectados ({systemState.detectedIssues.length})</span>
            </h3>
            {systemState.fixedIssues.length > 0 && (
              <span className="text-xs font-mono text-emerald-400">
                {systemState.fixedIssues.length} resolvidos
              </span>
            )}
          </div>

          <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
            {systemState.detectedIssues.length === 0 ? (
              <div className="rounded-lg bg-emerald-950/20 border border-emerald-500/20 p-4 text-center">
                <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto mb-1" />
                <p className="text-xs font-medium text-emerald-300">Nenhum problema pendente!</p>
                <p className="text-[11px] text-emerald-400/80 mt-0.5">O sistema está 100% otimizado e protegido.</p>
              </div>
            ) : (
              systemState.detectedIssues.map((issue, idx) => (
                <div 
                  key={idx} 
                  className="rounded-lg border border-slate-800/80 bg-slate-950/60 p-3 text-xs space-y-1.5"
                >
                  <div className="flex items-start gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                    <p className="text-slate-200 font-medium leading-relaxed">{issue}</p>
                  </div>
                </div>
              ))
            )}
          </div>

          {systemState.detectedIssues.length > 0 && (
            <button
              onClick={onRunAutoFix}
              disabled={systemState.isFixing}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 transition-colors shadow-sm disabled:opacity-50"
            >
              <span>Resolver Todos os {systemState.detectedIssues.length} Itens com 1 Clique</span>
            </button>
          )}
        </div>

        {/* Live PowerShell & Command Streaming Terminal Column */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden flex flex-col">
          {/* Terminal Window Header */}
          <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <span className="h-3 w-3 rounded-full bg-rose-500/80 inline-block" />
                <span className="h-3 w-3 rounded-full bg-amber-500/80 inline-block" />
                <span className="h-3 w-3 rounded-full bg-emerald-500/80 inline-block" />
              </div>
              <span className="text-xs font-mono font-medium text-slate-400 ml-2 flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-cyan-400" />
                <span>Console de Execução em Tempo Real (PowerShell / Windows Subprocess)</span>
              </span>
            </div>

            <button
              onClick={onClearLogs}
              title="Limpar console"
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors p-1"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>

          {/* Terminal Stream Body */}
          <div className="p-4 font-mono text-xs text-slate-300 space-y-1.5 h-[340px] overflow-y-auto leading-relaxed select-text">
            {systemState.terminalLogs.map((log, index) => {
              const isOk = log.includes('[OK]') || log.includes('[SUCESSO]');
              const isWarning = log.includes('[-]') || log.includes('[Aviso]') || log.includes('Violação');
              const isAutoFix = log.includes('[Auto-Fix]') || log.includes('===');
              const isCmd = log.includes('[SFC]') || log.includes('[DISM]') || log.includes('powershell') || log.includes('ipconfig');

              let textClass = 'text-slate-300';
              if (isOk) textClass = 'text-emerald-400';
              else if (isWarning) textClass = 'text-rose-400';
              else if (isAutoFix) textClass = 'text-cyan-400 font-bold';
              else if (isCmd) textClass = 'text-amber-300';

              return (
                <div key={index} className={textClass}>
                  {log}
                </div>
              );
            })}
          </div>

          {/* Terminal Footer status */}
          <div className="border-t border-slate-800/80 bg-slate-900/60 px-4 py-2 flex items-center justify-between text-[11px] font-mono text-slate-500">
            <span>Status do Processo: {systemState.isFixing ? 'Executando Auto-Fix...' : systemState.isDiagnosing ? 'Analisando Subsistemas...' : 'Ocioso'}</span>
            <span>UAC Session ID: 1 (Console)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
