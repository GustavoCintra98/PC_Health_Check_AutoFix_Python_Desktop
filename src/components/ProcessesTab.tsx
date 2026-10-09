import React, { useState } from 'react';
import { 
  Cpu, 
  Layers, 
  ShieldAlert, 
  ShieldCheck, 
  Trash2, 
  AlertTriangle, 
  PlusCircle, 
  Filter,
  CheckCircle2
} from 'lucide-react';
import { ProcessItem } from '../types/system';

interface ProcessesTabProps {
  processes: ProcessItem[];
  cpuUsage: number;
  ramUsagePercent: number;
  ramUsedGb: number;
  ramTotalGb: number;
  onKillProcess: (pid: number) => void;
  onSimulateHeavyProcess: () => void;
  onKillTopOffenders: () => void;
}

export const ProcessesTab: React.FC<ProcessesTabProps> = ({
  processes,
  cpuUsage,
  ramUsagePercent,
  ramUsedGb,
  ramTotalGb,
  onKillProcess,
  onSimulateHeavyProcess,
  onKillTopOffenders
}) => {
  const [filterType, setFilterType] = useState<'all' | 'user' | 'system'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Top 3 non-critical processes (Fase 1 requirement)
  const topCpuProcesses = [...processes]
    .filter(p => !p.isCritical && p.status === 'running')
    .sort((a, b) => b.cpu - a.cpu)
    .slice(0, 3);

  const topRamProcesses = [...processes]
    .filter(p => !p.isCritical && p.status === 'running')
    .sort((a, b) => b.memoryMb - a.memoryMb)
    .slice(0, 3);

  const filteredProcesses = processes.filter(p => {
    if (filterType === 'user' && p.isCritical) return false;
    if (filterType === 'system' && !p.isCritical) return false;
    if (searchQuery.trim() !== '') {
      return (
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.pid.toString().includes(searchQuery)
      );
    }
    return true;
  });

  const activeOffendersCount = topCpuProcesses.filter(p => p.cpu > 10).length;

  return (
    <div className="space-y-6">
      {/* Header Info Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Cpu className="h-5 w-5 text-cyan-400" />
              <span>Monitor & Gerenciador de Processos (CPU e Memória)</span>
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Identificação de gargalos em tempo real via <code className="text-cyan-400">psutil.process_iter()</code> com proteção contra finalização de processos críticos do kernel.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onSimulateHeavyProcess}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              <PlusCircle className="h-3.5 w-3.5 text-cyan-400" />
              <span>Simular Processo Pesado (+Loop)</span>
            </button>

            {activeOffendersCount > 0 && (
              <button
                onClick={onKillTopOffenders}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 rounded-lg shadow-sm transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Matar Maiores Consumidores ({activeOffendersCount})</span>
              </button>
            )}
          </div>
        </div>

        {/* Meters */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* CPU Meter */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="flex justify-between text-xs font-mono mb-2">
              <span className="text-slate-400">Carga Total de CPU</span>
              <span className="font-bold text-white">{cpuUsage.toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-300 ${cpuUsage > 80 ? 'bg-rose-500' : cpuUsage > 50 ? 'bg-amber-400' : 'bg-cyan-400'}`}
                style={{ width: `${Math.min(100, cpuUsage)}%` }}
              />
            </div>
            <div className="mt-2 text-[11px] text-slate-400 flex justify-between">
              <span>{cpuUsage > 80 ? '⚠️ Gargalo Crítico (>80%)' : 'Status: Normal'}</span>
              <span>Medido com psutil.cpu_percent()</span>
            </div>
          </div>

          {/* RAM Meter */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="flex justify-between text-xs font-mono mb-2">
              <span className="text-slate-400">Memória Física Utilizada</span>
              <span className="font-bold text-white">{ramUsedGb.toFixed(1)} GB / {ramTotalGb.toFixed(1)} GB ({ramUsagePercent.toFixed(0)}%)</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-300 ${ramUsagePercent > 80 ? 'bg-rose-500' : ramUsagePercent > 60 ? 'bg-amber-400' : 'bg-indigo-400'}`}
                style={{ width: `${Math.min(100, ramUsagePercent)}%` }}
              />
            </div>
            <div className="mt-2 text-[11px] text-slate-400 flex justify-between">
              <span>{ramUsagePercent > 85 ? '⚠️ Memória Quase Esgotada' : 'Status: Estável'}</span>
              <span>Disponível: {(ramTotalGb - ramUsedGb).toFixed(1)} GB</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top 3 Consumer Spotlights (Fase 1 Requirement) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top 3 CPU */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>Top 3 Processos Não-Críticos em CPU</span>
            <span className="text-[10px] text-cyan-400 font-mono">Fase 1: Diagnóstico</span>
          </h3>
          <div className="space-y-2">
            {topCpuProcesses.map((proc, i) => (
              <div key={proc.pid} className="flex items-center justify-between rounded-lg bg-slate-950/50 p-2.5 border border-slate-800/80 text-xs">
                <div>
                  <div className="font-semibold text-slate-200">{i + 1}. {proc.name}</div>
                  <div className="text-[11px] text-slate-400 font-mono">PID: {proc.pid} · RAM: {proc.memoryMb} MB</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-amber-400 tabular-nums">{proc.cpu.toFixed(1)}% CPU</span>
                  <button
                    onClick={() => onKillProcess(proc.pid)}
                    className="p-1 rounded hover:bg-rose-950/50 text-slate-400 hover:text-rose-400 transition-colors"
                    title="Encerrar Processo"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top 3 RAM */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>Top 3 Processos Não-Críticos em RAM</span>
            <span className="text-[10px] text-indigo-400 font-mono">Fase 1: Diagnóstico</span>
          </h3>
          <div className="space-y-2">
            {topRamProcesses.map((proc, i) => (
              <div key={proc.pid} className="flex items-center justify-between rounded-lg bg-slate-950/50 p-2.5 border border-slate-800/80 text-xs">
                <div>
                  <div className="font-semibold text-slate-200">{i + 1}. {proc.name}</div>
                  <div className="text-[11px] text-slate-400 font-mono">PID: {proc.pid} · CPU: {proc.cpu.toFixed(1)}%</div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-indigo-300 tabular-nums">{proc.memoryMb.toLocaleString()} MB</span>
                  <button
                    onClick={() => onKillProcess(proc.pid)}
                    className="p-1 rounded hover:bg-rose-950/50 text-slate-400 hover:text-rose-400 transition-colors"
                    title="Encerrar Processo"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Process Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
        {/* Table Filters & Search */}
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-slate-900/60">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-400">Filtrar:</span>
            <div className="flex items-center rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              <button
                onClick={() => setFilterType('all')}
                className={`px-2.5 py-1 rounded transition-colors ${filterType === 'all' ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Todos ({processes.length})
              </button>
              <button
                onClick={() => setFilterType('user')}
                className={`px-2.5 py-1 rounded transition-colors ${filterType === 'user' ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Usuário ({processes.filter(p => !p.isCritical).length})
              </button>
              <button
                onClick={() => setFilterType('system')}
                className={`px-2.5 py-1 rounded transition-colors ${filterType === 'system' ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Críticos do Sistema ({processes.filter(p => p.isCritical).length})
              </button>
            </div>
          </div>

          <div className="relative">
            <input
              type="text"
              placeholder="Buscar por nome ou PID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-64 rounded-lg bg-slate-950 border border-slate-800 px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Process Table Body */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-mono">
              <tr>
                <th className="py-2.5 px-4 font-medium">Nome do Processo</th>
                <th className="py-2.5 px-3 font-medium">PID</th>
                <th className="py-2.5 px-3 font-medium text-right">Uso de CPU</th>
                <th className="py-2.5 px-3 font-medium text-right">Memória RAM</th>
                <th className="py-2.5 px-4 font-medium">Proteção do Sistema</th>
                <th className="py-2.5 px-4 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredProcesses.map((proc) => {
                const isHog = !proc.isCritical && (proc.cpu > 15 || proc.memoryMb > 1000);
                const isTerminated = proc.status === 'terminated';

                return (
                  <tr key={proc.pid} className={`hover:bg-slate-800/30 transition-colors ${isTerminated ? 'opacity-40 line-through' : ''}`}>
                    <td className="py-3 px-4 font-sans font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        {isHog && <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />}
                        <span>{proc.name}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-sans">{proc.description}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-400 tabular-nums">{proc.pid}</td>
                    <td className="py-3 px-3 text-right tabular-nums">
                      <span className={proc.cpu > 15 ? 'text-amber-400 font-bold' : 'text-slate-300'}>
                        {proc.cpu.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right tabular-nums">
                      <span className={proc.memoryMb > 1000 ? 'text-indigo-300 font-bold' : 'text-slate-300'}>
                        {proc.memoryMb.toLocaleString()} MB
                      </span>
                    </td>
                    <td className="py-3 px-4 font-sans">
                      {proc.isCritical ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
                          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                          <span>Crítico (Kernel Protegido)</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
                          <ShieldAlert className="h-3.5 w-3.5 text-slate-500" />
                          <span>Espaço de Usuário</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {proc.isCritical ? (
                        <span className="text-[11px] text-slate-500 italic">Bloqueado por Segurança</span>
                      ) : isTerminated ? (
                        <span className="text-[11px] text-rose-400">Finalizado</span>
                      ) : (
                        <button
                          onClick={() => onKillProcess(proc.pid)}
                          className="px-2.5 py-1 rounded text-xs font-sans font-medium bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/40 transition-colors"
                        >
                          Encerrar Processo
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
