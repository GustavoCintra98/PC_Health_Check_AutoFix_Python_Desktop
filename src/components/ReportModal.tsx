import React, { useState } from 'react';
import { FileText, Copy, Download, Check, X, ShieldCheck } from 'lucide-react';
import { SystemHealthState } from '../types/system';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemState: SystemHealthState;
}

export const ReportModal: React.FC<ReportModalProps> = ({
  isOpen,
  onClose,
  systemState
}) => {
  const [copied, setCopied] = useState(false);
  const [format, setFormat] = useState<'markdown' | 'json'>('markdown');

  if (!isOpen) return null;

  const generateMarkdownReport = () => {
    const timestamp = new Date().toLocaleString('pt-BR');
    const totalTemp = systemState.storageCategories.reduce((acc, c) => acc + c.sizeMb, 0);

    return `# RELATÓRIO TÉCNICO DE DIAGNÓSTICO E REPARO DO SISTEMA
**Aplicativo:** PC Health Check & Auto-Fix v2.5 Professional
**Data/Hora:** ${timestamp}
**Ambiente:** Windows 11 Pro 64-bit | UAC: ${systemState.isAdmin ? 'Elevado (Administrador)' : 'Padrão (Restrito)'}

---

## 1. HARDWARE & RECURSOS DE PROCESSAMENTO
- **Processador:** ${systemState.cpuCores} Núcleos Físicos / ${systemState.cpuThreads} Threads
- **Uso de CPU:** ${systemState.cpuUsage.toFixed(1)}% (Gargalo: ${systemState.cpuUsage > 80 ? 'SIM' : 'NÃO'})
- **Memória RAM:** ${systemState.ramUsedGb} GB em uso de ${systemState.ramTotalGb} GB (${systemState.ramUsagePercent.toFixed(0)}%)
- **Processos Ativos:** ${systemState.processes.filter(p => p.status === 'running').length} processos monitorados

---

## 2. ARMAZENAMENTO & ARQUIVOS TEMPORÁRIOS
- **Unidades:**
${systemState.drives.map(d => `  - Unidade ${d.letter} [${d.label}]: ${d.freeGb} GB livres de ${d.totalGb} GB (${d.usedPercent}% em uso) | SMART: ${d.smartStatus} | Frag: ${d.fragmentationPercent}%`).join('\n')}
- **Volume de Temporários Identificados:** ${(totalTemp / 1024).toFixed(2)} GB
  - %TEMP% do Usuário: ${systemState.storageCategories.find(c => c.id === 'user_temp')?.sizeMb} MB
  - C:\\Windows\\Temp: ${systemState.storageCategories.find(c => c.id === 'win_temp')?.sizeMb} MB
  - Windows Prefetch: ${systemState.storageCategories.find(c => c.id === 'win_prefetch')?.sizeMb} MB
  - Lixeira do Windows: ${systemState.storageCategories.find(c => c.id === 'recycle_bin')?.sizeMb} MB

---

## 3. REDE E CONECTIVIDADE
- **Teste de Ping (8.8.8.8):** ${systemState.network.pingMs} ms
- **Perda de Pacotes:** ${systemState.network.packetLoss}%
- **Jitter:** ${systemState.network.jitterMs} ms
- **Status DNS:** ${systemState.network.dnsResolved ? 'Resolvido com sucesso' : 'Falha na resolução'}
- **Adaptadores:** ${systemState.network.adapters.map(a => `${a.name} (${a.speedMbps} Mbps)`).join(', ')}

---

## 4. INTEGRIDADE DO SO E SERVIÇOS
- **Integridade SFC (/verifyonly):** ${systemState.sfcStatus === 'corrupted' ? 'Violações detectadas (Requer reparo)' : '100% Íntegro'}
- **Status do Repositório DISM:** ${systemState.dismStatus === 'corrupted' ? 'Componentes WinSxS corrompidos' : 'Saudável'}
- **Serviços Críticos Monitorados:**
${systemState.services.map(s => `  - ${s.displayName} (${s.name}): [${s.status.toUpperCase()}] ${s.critical ? '- CRÍTICO' : ''}`).join('\n')}

---

## 5. RESUMO DE PROBLEMAS & AÇÕES
- **Problemas Pendentes:** ${systemState.detectedIssues.length}
${systemState.detectedIssues.map(i => `  * ${i}`).join('\n')}
- **Ações Executadas pelo Auto-Fix:** ${systemState.fixedIssues.length}
${systemState.fixedIssues.map(f => `  [OK] ${f}`).join('\n')}

---
*Gerado automaticamente pelo PC Health Check & Auto-Fix.*
`;
  };

  const reportText = format === 'markdown' 
    ? generateMarkdownReport() 
    : JSON.stringify(systemState, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(reportText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `PC_Health_Report_${Date.now()}.${format === 'markdown' ? 'md' : 'json'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <FileText className="h-5 w-5 text-cyan-400" />
            <div>
              <h3 className="text-base font-semibold text-white">Relatório Técnico de Diagnóstico</h3>
              <p className="text-xs text-slate-400">Exportação de métricas e ações de auditoria</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex rounded-lg bg-slate-900 p-0.5 border border-slate-800 text-xs">
              <button
                onClick={() => setFormat('markdown')}
                className={`px-2.5 py-1 rounded transition-colors ${format === 'markdown' ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400'}`}
              >
                Markdown (.md)
              </button>
              <button
                onClick={() => setFormat('json')}
                className={`px-2.5 py-1 rounded transition-colors ${format === 'json' ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400'}`}
              >
                JSON (.json)
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto font-mono text-xs text-slate-300 bg-slate-950 leading-relaxed select-text flex-1">
          <pre className="whitespace-pre-wrap">{reportText}</pre>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/80 px-6 py-3">
          <span className="text-xs text-slate-400 font-mono">
            {format === 'markdown' ? 'Formato Markdown legível para relatórios' : 'JSON estruturado para integração'}
          </span>

          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? 'Copiado!' : 'Copiar Texto'}</span>
            </button>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors shadow-sm"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Baixar Arquivo</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
