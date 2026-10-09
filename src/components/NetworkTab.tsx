import React, { useState } from 'react';
import { 
  Wifi, 
  RotateCw, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Server, 
  Terminal,
  ShieldCheck,
  RefreshCw,
  Globe
} from 'lucide-react';
import { NetworkStatus } from '../types/system';

interface NetworkTabProps {
  network: NetworkStatus;
  onFlushDns: () => void;
  onResetWinsock: () => void;
  onRunPingTest: () => void;
  isTesting: boolean;
}

export const NetworkTab: React.FC<NetworkTabProps> = ({
  network,
  onFlushDns,
  onResetWinsock,
  onRunPingTest,
  isTesting
}) => {
  const [selectedTarget, setSelectedTarget] = useState<'google' | 'cloudflare'>('google');

  return (
    <div className="space-y-6">
      {/* Network Overview Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Wifi className="h-5 w-5 text-emerald-400" />
              <span>Diagnóstico de Rede & Resolução Winsock</span>
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Varredura de latência ICMP, perda de pacotes, adaptadores de interface e comandos de restauração de pilha TCP/IP e resolvedor DNS.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onRunPingTest}
              disabled={isTesting}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isTesting ? 'animate-spin text-emerald-400' : ''}`} />
              <span>{isTesting ? 'Pingando 8.8.8.8...' : 'Executar Teste de Ping'}</span>
            </button>
          </div>
        </div>

        {/* Live Metrics Grid */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Latency */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="text-xs font-mono text-slate-400">Latência ICMP (Ping 8.8.8.8)</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-white tabular-nums">
                {network.pingMs}
              </span>
              <span className="text-xs font-mono text-slate-400">ms</span>
            </div>
            <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${network.pingMs < 50 ? 'bg-emerald-400' : network.pingMs < 100 ? 'bg-amber-400' : 'bg-rose-500'}`} />
              <span>{network.pingMs < 50 ? 'Excelente (Baixa Latência)' : network.pingMs < 100 ? 'Moderado' : 'Alta Latência Detectada'}</span>
            </div>
          </div>

          {/* Packet Loss */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="text-xs font-mono text-slate-400">Perda de Pacotes (Packet Loss)</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className={`text-3xl font-bold font-mono tabular-nums ${network.packetLoss > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                {network.packetLoss}%
              </span>
            </div>
            <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${network.packetLoss === 0 ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span>{network.packetLoss === 0 ? '0% de Perda (Conexão Íntegra)' : 'Instabilidade / Perda de Pacotes'}</span>
            </div>
          </div>

          {/* Jitter & DNS */}
          <div className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
            <div className="text-xs font-mono text-slate-400">Jitter & Resolvedor DNS</div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-white tabular-nums">
                {network.jitterMs}
              </span>
              <span className="text-xs font-mono text-slate-400">ms jitter</span>
            </div>
            <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
              <CheckCircle2 className="h-3 w-3 text-emerald-400" />
              <span>DNS Resolvendo com Sucesso</span>
            </div>
          </div>
        </div>
      </div>

      {/* Network Auto-Fix Action Tools */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Terminal className="h-4 w-4 text-cyan-400" />
          <span>Fase 2: Ferramentas de Resolução de Conectividade e Pilha de Rede</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Flush DNS Tool */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-200">Limpar Cache DNS (Flush DNS)</span>
                <span className="text-[10px] font-mono text-cyan-400">ipconfig /flushdns</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Esvazia o cache do resolvedor DNS do Windows, corrigindo falhas de navegação para sites que mudaram de IP ou entradas corrompidas.
              </p>
            </div>
            <button
              onClick={onFlushDns}
              className="w-full py-2 px-3 rounded-lg text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors flex items-center justify-center gap-2"
            >
              <RotateCw className="h-3.5 w-3.5 text-cyan-400" />
              <span>Executar ipconfig /flushdns</span>
            </button>
          </div>

          {/* Reset Winsock & TCP/IP */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 flex flex-col justify-between space-y-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-200">Redefinir Catálogo Winsock & IP</span>
                <span className="text-[10px] font-mono text-amber-400">netsh winsock reset</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Restaura as configurações de fábrica da pilha de rede e do catálogo de sockets do Windows para solucionar perda total de conexão.
              </p>
            </div>
            <button
              onClick={onResetWinsock}
              className="w-full py-2 px-3 rounded-lg text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 transition-colors flex items-center justify-center gap-2"
            >
              <Activity className="h-3.5 w-3.5" />
              <span>Redefinir Winsock & Liberar/Renovar IP</span>
            </button>
          </div>
        </div>
      </div>

      {/* Network Adapters List */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <Server className="h-4 w-4 text-emerald-400" />
          <span>Adaptadores de Rede Detectados (psutil.net_if_stats)</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {network.adapters.map((adapter, i) => (
            <div key={i} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-xs flex items-center justify-between">
              <div className="space-y-1">
                <div className="font-semibold text-slate-200 flex items-center gap-2">
                  <span>{adapter.name}</span>
                  <span className="text-[10px] rounded bg-slate-800 px-1.5 py-0.2 text-slate-400">
                    {adapter.type}
                  </span>
                </div>
                <div className="font-mono text-[11px] text-slate-400">
                  IP: {adapter.ip} · Velocidade de Link: {adapter.speedMbps} Mbps
                </div>
              </div>

              <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span>Ativo (UP)</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
