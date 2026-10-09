import React, { useState } from 'react';
import { Header } from './components/Header';
import { DashboardTab } from './components/DashboardTab';
import { ProcessesTab } from './components/ProcessesTab';
import { StorageTab } from './components/StorageTab';
import { NetworkTab } from './components/NetworkTab';
import { ServicesTab } from './components/ServicesTab';
import { PythonCodeTab } from './components/PythonCodeTab';
import { UACPromptModal } from './components/UACPromptModal';
import { ReportModal } from './components/ReportModal';
import { getInitialSystemHealthState } from './data/initialSystemData';
import { SystemHealthState } from './types/system';

export default function App() {
  const [systemState, setSystemState] = useState<SystemHealthState>(getInitialSystemHealthState());
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isUACModalOpen, setIsUACModalOpen] = useState<boolean>(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState<boolean>(false);
  const [isTestingNetwork, setIsTestingNetwork] = useState<boolean>(false);

  // Helper to append a timestamped log to the real-time terminal
  const appendLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString('pt-BR');
    setSystemState(prev => ({
      ...prev,
      terminalLogs: [...prev.terminalLogs, `[${timestamp}] ${message}`]
    }));
  };

  // ------------------ FASE 1: ANÁLISE COMPLETA (DIAGNÓSTICO) ------------------
  const handleRunDiagnosis = async () => {
    if (systemState.isDiagnosing || systemState.isFixing) return;

    setSystemState(prev => ({ ...prev, isDiagnosing: true }));
    appendLog('=== INICIANDO FASE 1: ANÁLISE COMPLETA DO SISTEMA (DIAGNÓSTICO) ===');

    // 1. CPU & Memória
    appendLog('[Diagnóstico] Analisando uso de CPU e Memória RAM via psutil...');
    await new Promise(r => setTimeout(r, 600));

    // 2. Armazenamento & Discos
    appendLog('[Diagnóstico] Verificando unidades fixas, saúde S.M.A.R.T. e arquivos temporários...');
    await new Promise(r => setTimeout(r, 600));

    // 3. Rede e Conectividade
    appendLog('[Diagnóstico] Executando ping para 8.8.8.8 (Google DNS) e inspecionando adaptadores...');
    await new Promise(r => setTimeout(r, 600));

    // 4. Sistema Operacional & Serviços
    appendLog('[Diagnóstico] Verificando integridade SFC (/verifyonly) e serviços essenciais do Windows...');
    await new Promise(r => setTimeout(r, 800));

    const timestamp = new Date().toLocaleTimeString('pt-BR');
    
    setSystemState(prev => {
      const issues: string[] = [];

      if (prev.cpuUsage > 75) {
        issues.push(`Uso elevado de CPU detectado (${prev.cpuUsage.toFixed(1)}%)`);
      }
      if (prev.ramUsagePercent > 80) {
        issues.push(`Memória RAM sobrecarregada (${prev.ramUsagePercent.toFixed(0)}% em uso)`);
      }
      
      const uncleanedTemp = prev.storageCategories.filter(c => !c.isCleaned);
      const totalTempMb = uncleanedTemp.reduce((a, b) => a + b.sizeMb, 0);
      if (totalTempMb > 500) {
        issues.push(`Acúmulo de arquivos temporários e cache: ${(totalTempMb / 1024).toFixed(1)} GB`);
      }

      if (prev.network.packetLoss > 0) {
        issues.push(`Instabilidade de rede: ${prev.network.packetLoss}% de perda de pacotes`);
      }

      if (prev.sfcStatus === 'corrupted') {
        issues.push('Violações de integridade detectadas no repositório de componentes do Windows');
      }

      const stoppedCrit = prev.services.filter(s => s.critical && s.status === 'Stopped');
      stoppedCrit.forEach(s => {
        issues.push(`Serviço essencial parado: ${s.displayName} (${s.name})`);
      });

      return {
        ...prev,
        isDiagnosing: false,
        lastDiagnosisTime: timestamp,
        detectedIssues: issues
      };
    });

    appendLog('[OK] Fase 1 finalizada. Varredura concluída em todos os subsistemas.');
  };

  // ------------------ FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ------------------
  const handleRunAutoFix = async () => {
    if (systemState.isFixing || systemState.isDiagnosing) return;

    setSystemState(prev => ({ ...prev, isFixing: true }));
    appendLog('=== INICIANDO FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ===');

    // 1. Armazenamento: Limpeza de %TEMP%, Prefetch e Lixeira
    appendLog('[Auto-Fix] 1/4 Otimizando armazenamento: limpando %TEMP%, Prefetch e esvaziando Lixeira...');
    await new Promise(r => setTimeout(r, 700));
    appendLog('  -> Limpeza segura: ignorados arquivos atualmente bloqueados em uso (PermissionError silenciado)');
    appendLog('  -> Esvaziamento da Lixeira concluído com sucesso');
    
    // 2. Reparo de Rede: Flush DNS, release/renew e Winsock
    appendLog('[Auto-Fix] 2/4 Restaurando conectividade de rede e redefinindo catálogo Winsock...');
    await new Promise(r => setTimeout(r, 700));
    appendLog('  -> Executado: ipconfig /flushdns (Cache DNS limpo com êxito)');
    appendLog('  -> Executado: netsh winsock reset (Catálogo Winsock redefinido)');
    appendLog('  -> Executado: netsh int ip reset (Pilha TCP/IP restaurada)');

    // 3. Integridade do SO & Serviços
    appendLog('[Auto-Fix] 3/4 Verificando e reparando integridade de arquivos do Windows (SFC /scannow & DISM)...');
    await new Promise(r => setTimeout(r, 900));
    appendLog('  -> [SFC] O Windows Resource Protection encontrou arquivos corrompidos e os reparou com êxito.');
    appendLog('  -> [DISM] A operação de restauração de integridade da imagem foi concluída com êxito (100.0%).');
    appendLog('  -> Reiniciando serviços essenciais parados (wuauserv, bits)...');

    // 4. Gerenciamento de Processos: matar processos não críticos ofensores
    appendLog('[Auto-Fix] 4/4 Encerrando processos de usuário ofensores de CPU/RAM (mantendo processos críticos do kernel protegidos)...');
    await new Promise(r => setTimeout(r, 600));

    setSystemState(prev => {
      // Clean all storage categories
      const updatedStorage = prev.storageCategories.map(c => ({
        ...c,
        isCleaned: true
      }));

      // Free disk space on drive C:
      const freedGb = Number((prev.storageCategories.reduce((a, b) => a + b.sizeMb, 0) / 1024).toFixed(1));
      const updatedDrives = prev.drives.map(d => {
        if (d.letter === 'C:') {
          const newFree = Math.min(d.totalGb, Number((d.freeGb + freedGb).toFixed(1)));
          const newUsed = Number((((d.totalGb - newFree) / d.totalGb) * 100).toFixed(1));
          return { ...d, freeGb: newFree, usedPercent: newUsed };
        }
        return d;
      });

      // Kill offending user tasks
      const updatedProcesses = prev.processes.map(p => {
        if (!p.isCritical && (p.cpu > 15 || p.name.includes('unresponsive'))) {
          return { ...p, status: 'terminated' as const, cpu: 0, memoryMb: 0 };
        }
        return p;
      });

      // Restart stopped services
      const updatedServices = prev.services.map(s => ({
        ...s,
        status: 'Running' as const
      }));

      // Network optimized
      const updatedNetwork = {
        ...prev.network,
        pingMs: 24,
        packetLoss: 0,
        jitterMs: 3
      };

      const fixedList = [
        `Armazenamento: ${freedGb} GB de arquivos temporários, Prefetch e Lixeira eliminados`,
        'Rede: Catálogo Winsock e pilha TCP/IP redefinidos (Ping 24ms, 0% perda)',
        'SO: SFC /scannow e DISM repararam arquivos de componentes com sucesso',
        'Serviços: Windows Update (wuauserv) e BITS iniciados com sucesso',
        'Processos: Tarefas órfãs e ofensoras de CPU encerradas com segurança'
      ];

      return {
        ...prev,
        isFixing: false,
        cpuUsage: 14.8,
        ramUsagePercent: 38.0,
        ramUsedGb: Number((prev.ramTotalGb * 0.38).toFixed(1)),
        storageCategories: updatedStorage,
        drives: updatedDrives,
        processes: updatedProcesses,
        services: updatedServices,
        network: updatedNetwork,
        sfcStatus: 'repaired',
        dismStatus: 'healthy',
        detectedIssues: [],
        fixedIssues: fixedList
      };
    });

    appendLog('[SUCESSO] === FASE 2: RESOLUÇÃO AUTOMÁTICA FINALIZADA COM SUCESSO! ===');
    appendLog('[OK] O computador está totalmente otimizado e com integridade de arquivos restaurada.');
  };

  // ------------------ GERENCIADOR DE PROCESSOS ------------------
  const handleKillProcess = (pid: number) => {
    const target = systemState.processes.find(p => p.pid === pid);
    if (!target) return;

    if (target.isCritical) {
      appendLog(`[-] Tentativa de finalizar processo crítico bloqueada: ${target.name} (PID: ${pid}) - Protegido contra BSOD`);
      return;
    }

    setSystemState(prev => {
      const updatedProcs = prev.processes.map(p => {
        if (p.pid === pid) {
          return { ...p, status: 'terminated' as const, cpu: 0, memoryMb: 0 };
        }
        return p;
      });

      const newCpu = Math.max(8, prev.cpuUsage - target.cpu);
      const newRamMb = Math.max(2000, (prev.ramUsedGb * 1024) - target.memoryMb);
      const newRamGb = Number((newRamMb / 1024).toFixed(1));
      const newRamPct = Number(((newRamGb / prev.ramTotalGb) * 100).toFixed(0));

      return {
        ...prev,
        processes: updatedProcs,
        cpuUsage: Number(newCpu.toFixed(1)),
        ramUsedGb: newRamGb,
        ramUsagePercent: newRamPct,
        detectedIssues: prev.detectedIssues.filter(i => !i.includes(target.name))
      };
    });

    appendLog(`[OK] Processo de usuário encerrado: ${target.name} (PID: ${pid})`);
  };

  const handleSimulateHeavyProcess = () => {
    const newPid = Math.floor(10000 + Math.random() * 80000);
    const newProc = {
      pid: newPid,
      name: 'heavy_render_task.exe',
      cpu: 34.5,
      memoryMb: 1450,
      isCritical: false,
      status: 'running' as const,
      description: 'Processo de teste simulando carga pesada de CPU'
    };

    setSystemState(prev => ({
      ...prev,
      cpuUsage: Math.min(99, prev.cpuUsage + 28),
      ramUsedGb: Number((prev.ramUsedGb + 1.4).toFixed(1)),
      ramUsagePercent: Math.min(98, prev.ramUsagePercent + 12),
      processes: [newProc, ...prev.processes],
      detectedIssues: [...prev.detectedIssues, `Novo gargalo de CPU detectado: ${newProc.name} (${newProc.cpu}%)`]
    }));

    appendLog(`[TESTE] Processo pesado iniciado: ${newProc.name} (PID: ${newPid}) consumindo 34.5% de CPU.`);
  };

  const handleKillTopOffenders = () => {
    const offenders = systemState.processes.filter(p => !p.isCritical && p.status === 'running' && p.cpu > 10);
    offenders.forEach(p => handleKillProcess(p.pid));
  };

  // ------------------ ARMAZENAMENTO ------------------
  const handleCleanCategory = (id: string) => {
    const cat = systemState.storageCategories.find(c => c.id === id);
    if (!cat) return;

    setSystemState(prev => ({
      ...prev,
      storageCategories: prev.storageCategories.map(c => c.id === id ? { ...c, isCleaned: true } : c)
    }));

    appendLog(`[OK] Limpeza concluída em ${cat.name}: ${cat.fileCount} arquivos removidos (${cat.sizeMb} MB liberados).`);
  };

  const handleCleanAllStorage = () => {
    const totalFreed = systemState.storageCategories
      .filter(c => !c.isCleaned)
      .reduce((a, b) => a + b.sizeMb, 0);

    setSystemState(prev => {
      const updatedCategories = prev.storageCategories.map(c => ({ ...c, isCleaned: true }));
      const freedGb = Number((totalFreed / 1024).toFixed(1));
      const updatedDrives = prev.drives.map(d => {
        if (d.letter === 'C:') {
          const newFree = Number((d.freeGb + freedGb).toFixed(1));
          return { ...d, freeGb: newFree, usedPercent: Number((((d.totalGb - newFree) / d.totalGb) * 100).toFixed(1)) };
        }
        return d;
      });

      return {
        ...prev,
        storageCategories: updatedCategories,
        drives: updatedDrives,
        detectedIssues: prev.detectedIssues.filter(i => !i.includes('temporários') && !i.includes('disco'))
      };
    });

    appendLog(`[OK] Limpeza global de disco concluída: ${(totalFreed / 1024).toFixed(2)} GB liberados com sucesso.`);
  };

  // ------------------ REDE ------------------
  const handleFlushDns = () => {
    appendLog('[DNS] Executando comando: ipconfig /flushdns...');
    setTimeout(() => {
      appendLog('[OK] Configuração de IP do Windows: Liberação do cache do resolvedor DNS bem-sucedida.');
    }, 400);
  };

  const handleResetWinsock = () => {
    appendLog('[WINSOCK] Executando comando: netsh winsock reset...');
    setTimeout(() => {
      appendLog('[OK] O Catálogo Winsock foi redefinido com êxito.');
      appendLog('[IP] Executando comando: netsh int ip reset...');
      setSystemState(prev => ({
        ...prev,
        network: { ...prev.network, pingMs: 22, packetLoss: 0, jitterMs: 2 },
        detectedIssues: prev.detectedIssues.filter(i => !i.includes('rede') && !i.includes('pacotes'))
      }));
      appendLog('[OK] Redefinição de Interface IPv4 e IPv6 concluída. Conectividade restaurada.');
    }, 600);
  };

  const handleRunPingTest = async () => {
    setIsTestingNetwork(true);
    appendLog('[Ping] Disparando 4 pacotes ICMP para 8.8.8.8 com timeout de 2000ms...');

    // Sample real fetch latency to cloudflare or fallback
    let sampledLatency = 28;
    try {
      const start = performance.now();
      await fetch('https://www.google.com/favicon.ico', { mode: 'no-cors', cache: 'no-cache' });
      sampledLatency = Math.max(12, Math.round(performance.now() - start));
    } catch {
      sampledLatency = Math.floor(18 + Math.random() * 20);
    }

    setTimeout(() => {
      setIsTestingNetwork(false);
      setSystemState(prev => ({
        ...prev,
        network: {
          ...prev.network,
          pingMs: sampledLatency,
          packetLoss: 0,
          jitterMs: Math.floor(Math.random() * 4) + 1
        }
      }));
      appendLog(`[OK] Resposta de 8.8.8.8: bytes=32 tempo=${sampledLatency}ms TTL=118 (0% de perda).`);
    }, 800);
  };

  // ------------------ SO E SERVIÇOS ------------------
  const handleRunSfcScan = () => {
    appendLog('[SFC] Iniciando fase de verificação de verificação do sistema...');
    appendLog('[SFC] Iniciando a verificação de 100% dos arquivos de sistema...');
    setTimeout(() => {
      setSystemState(prev => ({
        ...prev,
        sfcStatus: 'repaired',
        detectedIssues: prev.detectedIssues.filter(i => !i.includes('SFC') && !i.includes('integridade'))
      }));
      appendLog('[OK] O Windows Resource Protection encontrou arquivos corrompidos e os reparou com êxito.');
      appendLog('[OK] Detalhes incluídos no CBS.Log (%windir%\\Logs\\CBS\\CBS.log).');
    }, 1200);
  };

  const handleRunDismRepair = () => {
    appendLog('[DISM] Ferramenta de Gerenciamento e Manutenção de Imagens de Implantação...');
    appendLog('[DISM] Verificando integridade da imagem do Windows...');
    setTimeout(() => {
      setSystemState(prev => ({
        ...prev,
        dismStatus: 'healthy'
      }));
      appendLog('[OK] Reparo de componentes concluído com êxito: A operação foi concluída com êxito (100.0%).');
    }, 1200);
  };

  const handleStartService = (serviceName: string) => {
    appendLog(`[SERVIÇO] Enviando comando: sc start ${serviceName}...`);
    setTimeout(() => {
      setSystemState(prev => ({
        ...prev,
        services: prev.services.map(s => s.name === serviceName ? { ...s, status: 'Running' as const } : s),
        detectedIssues: prev.detectedIssues.filter(i => !i.includes(serviceName))
      }));
      appendLog(`[OK] O serviço '${serviceName}' foi iniciado com êxito no status RUNNING.`);
    }, 500);
  };

  const handleRestartAllStoppedServices = () => {
    const stopped = systemState.services.filter(s => s.status === 'Stopped');
    stopped.forEach(s => handleStartService(s.name));
  };

  // ------------------ UAC TOGGLE ------------------
  const handleToggleAdmin = () => {
    if (!systemState.isAdmin) {
      setIsUACModalOpen(true);
    } else {
      // Toggle to non-admin for testing purposes
      setSystemState(prev => ({ ...prev, isAdmin: false }));
      appendLog('[UAC] Alternado para modo restrito (Usuário Padrão). Operações privilegiadas exigirão elevação.');
    }
  };

  const handleConfirmUACElevation = () => {
    setIsUACModalOpen(false);
    setSystemState(prev => ({ ...prev, isAdmin: true }));
    appendLog('[UAC] Elevação concedida pelo usuário: IsUserAnAdmin() == TRUE. Privilégios completos habilitados.');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Bar Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isAdmin={systemState.isAdmin}
        onToggleAdmin={handleToggleAdmin}
        onRunDiagnosis={handleRunDiagnosis}
        onRunAutoFix={handleRunAutoFix}
        onOpenReport={() => setIsReportModalOpen(true)}
        isDiagnosing={systemState.isDiagnosing}
        isFixing={systemState.isFixing}
        unresolvedCount={systemState.detectedIssues.length}
      />

      {/* Main Workspace Viewport */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'dashboard' && (
          <DashboardTab
            systemState={systemState}
            onRunDiagnosis={handleRunDiagnosis}
            onRunAutoFix={handleRunAutoFix}
            onNavigateTab={setActiveTab}
            onClearLogs={() => setSystemState(prev => ({ ...prev, terminalLogs: ['[CONSOLE] Console limpo pelo usuário.'] }))}
          />
        )}

        {activeTab === 'processes' && (
          <ProcessesTab
            processes={systemState.processes}
            cpuUsage={systemState.cpuUsage}
            ramUsagePercent={systemState.ramUsagePercent}
            ramUsedGb={systemState.ramUsedGb}
            ramTotalGb={systemState.ramTotalGb}
            onKillProcess={handleKillProcess}
            onSimulateHeavyProcess={handleSimulateHeavyProcess}
            onKillTopOffenders={handleKillTopOffenders}
          />
        )}

        {activeTab === 'storage' && (
          <StorageTab
            storageCategories={systemState.storageCategories}
            drives={systemState.drives}
            isAdmin={systemState.isAdmin}
            onCleanCategory={handleCleanCategory}
            onCleanAllStorage={handleCleanAllStorage}
          />
        )}

        {activeTab === 'network' && (
          <NetworkTab
            network={systemState.network}
            onFlushDns={handleFlushDns}
            onResetWinsock={handleResetWinsock}
            onRunPingTest={handleRunPingTest}
            isTesting={isTestingNetwork}
          />
        )}

        {activeTab === 'os_services' && (
          <ServicesTab
            services={systemState.services}
            sfcStatus={systemState.sfcStatus}
            dismStatus={systemState.dismStatus}
            isAdmin={systemState.isAdmin}
            onRunSfcScan={handleRunSfcScan}
            onRunDismRepair={handleRunDismRepair}
            onStartService={handleStartService}
            onRestartAllStoppedServices={handleRestartAllStoppedServices}
            isProcessing={systemState.isFixing}
          />
        )}

        {activeTab === 'python_code' && (
          <PythonCodeTab />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500 font-mono">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>PC Health Check & Auto-Fix · Arquitetura Modular Windows & Python CustomTkinter</span>
          <span>SFC / DISM / psutil / WMI / Winsock Automation Engine</span>
        </div>
      </footer>

      {/* UAC Elevation Modal */}
      <UACPromptModal
        isOpen={isUACModalOpen}
        onConfirm={handleConfirmUACElevation}
        onCancel={() => setIsUACModalOpen(false)}
        isAdmin={systemState.isAdmin}
      />

      {/* Technical Report Export Modal */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        systemState={systemState}
      />
    </div>
  );
}
