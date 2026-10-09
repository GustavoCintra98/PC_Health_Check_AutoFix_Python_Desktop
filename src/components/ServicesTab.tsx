import React from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  RotateCw, 
  Play, 
  Server, 
  Terminal, 
  Sparkles,
  Layers,
  Wrench
} from 'lucide-react';
import { WindowsService } from '../types/system';

interface ServicesTabProps {
  services: WindowsService[];
  sfcStatus: 'healthy' | 'corrupted' | 'unverified' | 'repaired';
  dismStatus: 'healthy' | 'corrupted' | 'repaired' | 'unverified';
  isAdmin: boolean;
  onRunSfcScan: () => void;
  onRunDismRepair: () => void;
  onStartService: (serviceName: string) => void;
  onRestartAllStoppedServices: () => void;
  isProcessing: boolean;
}

export const ServicesTab: React.FC<ServicesTabProps> = ({
  services,
  sfcStatus,
  dismStatus,
  isAdmin,
  onRunSfcScan,
  onRunDismRepair,
  onStartService,
  onRestartAllStoppedServices,
  isProcessing
}) => {
  const stoppedCritical = services.filter(s => s.critical && s.status === 'Stopped');
  const allStopped = services.filter(s => s.status === 'Stopped');

  return (
    <div className="space-y-6">
      {/* OS Integrity Header Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-purple-400" />
              <span>Integridade do Sistema Operacional & Serviços Windows</span>
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Varredura de repositório de componentes WinSxS com <code className="text-cyan-400">sfc /scannow</code> e <code className="text-cyan-400">DISM</code>, além de monitoramento de serviços essenciais parados.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <button
              onClick={onRunSfcScan}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RotateCw className={`h-3.5 w-3.5 ${isProcessing ? 'animate-spin text-purple-400' : ''}`} />
              <span>Executar sfc /scannow</span>
            </button>

            <button
              onClick={onRunDismRepair}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-950 transition-colors disabled:opacity-50"
            >
              <Wrench className="h-3.5 w-3.5" />
              <span>Executar Reparo DISM /RestoreHealth</span>
            </button>
          </div>
        </div>

        {/* SFC & DISM Status Badges */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* SFC Card */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200">SFC (System File Checker)</span>
              <span className="font-mono text-[11px] text-slate-400">sfc /scannow</span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              {sfcStatus === 'corrupted' ? (
                <div className="flex items-center gap-2 text-rose-400 text-sm font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Violações de Integridade Detectadas</span>
                </div>
              ) : sfcStatus === 'repaired' ? (
                <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Arquivos Corrompidos Reparados com Sucesso</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Repositório Íntegro (Sem Violações)</span>
                </div>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {sfcStatus === 'corrupted'
                ? 'Arquivos protegidos do Windows foram modificados ou corrompidos. Execute o reparo automático.'
                : 'Todas as assinaturas digitais de DLLs e executáveis de sistema estão válidas.'}
            </p>
          </div>

          {/* DISM Card */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-200">DISM (Deployment Image Servicing)</span>
              <span className="font-mono text-[11px] text-slate-400">DISM /RestoreHealth</span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              {dismStatus === 'corrupted' ? (
                <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Repositório de Componentes WinSxS Precisa de Reparo</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Imagem do Windows Saudável</span>
                </div>
              )}
            </div>
            <p className="mt-2 text-xs text-slate-400">
              Utiliza a fonte de atualização do Windows para rebaixar componentes corrompidos do armazenamento de componentes.
            </p>
          </div>
        </div>
      </div>

      {/* Services List Panel */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan-400" />
              <span>Serviços Essenciais do Windows ({services.length})</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Monitoramento via <code className="text-slate-300">psutil.win_service_get()</code> e comando <code className="text-slate-300">sc query</code>.
            </p>
          </div>

          {allStopped.length > 0 && (
            <button
              onClick={onRestartAllStoppedServices}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 transition-colors shadow-sm"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Iniciar Todos os Serviços Parados ({allStopped.length})</span>
            </button>
          )}
        </div>

        {/* Services Table */}
        <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/60">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-slate-800 text-slate-400 font-mono">
              <tr>
                <th className="py-2.5 px-4 font-medium">Nome do Serviço</th>
                <th className="py-2.5 px-3 font-medium">Identificador Técnico</th>
                <th className="py-2.5 px-3 font-medium">Status Atual</th>
                <th className="py-2.5 px-3 font-medium">Criticidade</th>
                <th className="py-2.5 px-4 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {services.map((srv) => {
                const isRunning = srv.status === 'Running';
                return (
                  <tr key={srv.name} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-200">
                      <div>{srv.displayName}</div>
                      <div className="text-[11px] text-slate-500">{srv.description}</div>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">{srv.name}</td>
                    <td className="py-3 px-3 font-mono">
                      {isRunning ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                          <span className="h-2 w-2 rounded-full bg-emerald-400" />
                          <span>Em Execução</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-rose-400 font-semibold">
                          <span className="h-2 w-2 rounded-full bg-rose-400 animate-ping" />
                          <span>Parado</span>
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {srv.critical ? (
                        <span className="text-[10px] rounded bg-rose-950/50 border border-rose-800/40 px-1.5 py-0.5 text-rose-300 font-medium">
                          Crítico
                        </span>
                      ) : (
                        <span className="text-[10px] rounded bg-slate-800 px-1.5 py-0.5 text-slate-400 font-medium">
                          Secundário
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {!isRunning ? (
                        <button
                          onClick={() => onStartService(srv.name)}
                          className="px-2.5 py-1 rounded text-xs font-medium bg-cyan-950/60 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800/40 transition-colors inline-flex items-center gap-1.5"
                        >
                          <Play className="h-3 w-3" />
                          <span>Iniciar Serviço</span>
                        </button>
                      ) : (
                        <span className="text-[11px] text-emerald-400/80 font-mono">OK</span>
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
