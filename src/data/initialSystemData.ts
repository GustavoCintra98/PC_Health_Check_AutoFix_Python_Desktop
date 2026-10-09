import { SystemHealthState, ProcessItem, StorageCategory, DiskDrive, WindowsService } from '../types/system';

export const INITIAL_PROCESSES: ProcessItem[] = [
  {
    pid: 14208,
    name: 'chrome.exe (Renderer Hog)',
    cpu: 28.4,
    memoryMb: 1840,
    isCritical: false,
    status: 'running',
    description: 'Processo de usuário com abas pesadas e renderização em segundo plano'
  },
  {
    pid: 9812,
    name: 'discord.exe',
    cpu: 14.2,
    memoryMb: 760,
    isCritical: false,
    status: 'running',
    description: 'Cliente de comunicação Discord com aceleração por hardware'
  },
  {
    pid: 2104,
    name: 'unresponsive_task.exe',
    cpu: 31.8,
    memoryMb: 1220,
    isCritical: false,
    status: 'running',
    description: 'Processo órfão de usuário em loop de processamento intenso'
  },
  {
    pid: 884,
    name: 'explorer.exe',
    cpu: 1.8,
    memoryMb: 185,
    isCritical: true,
    status: 'running',
    description: 'Interface de usuário do Windows Explorer e Barra de Tarefas'
  },
  {
    pid: 1256,
    name: 'svchost.exe (netsvcs)',
    cpu: 2.1,
    memoryMb: 210,
    isCritical: true,
    status: 'running',
    description: 'Host de Serviços Compartilhados do Windows (Rede e Autenticação)'
  },
  {
    pid: 624,
    name: 'dwm.exe',
    cpu: 3.4,
    memoryMb: 145,
    isCritical: true,
    status: 'running',
    description: 'Desktop Window Manager (Composição gráfica do Windows)'
  },
  {
    pid: 4,
    name: 'System',
    cpu: 0.8,
    memoryMb: 95,
    isCritical: true,
    status: 'running',
    description: 'Kernel do Windows NT e threads de sistema'
  },
  {
    pid: 7416,
    name: 'Spotify.exe',
    cpu: 4.2,
    memoryMb: 390,
    isCritical: false,
    status: 'running',
    description: 'Reprodutor de áudio e streaming de mídia'
  },
  {
    pid: 15320,
    name: 'OneDrive.exe',
    cpu: 6.5,
    memoryMb: 280,
    isCritical: false,
    status: 'running',
    description: 'Sincronizador de arquivos em nuvem'
  },
  {
    pid: 3180,
    name: 'MsMpEng.exe',
    cpu: 3.1,
    memoryMb: 290,
    isCritical: true,
    status: 'running',
    description: 'Motor de proteção em tempo real do Microsoft Defender'
  }
];

export const INITIAL_STORAGE_CATEGORIES: StorageCategory[] = [
  {
    id: 'user_temp',
    name: 'Arquivos Temporários do Usuário (%TEMP%)',
    path: 'C:\\Users\\Default\\AppData\\Local\\Temp',
    sizeMb: 1420.5,
    fileCount: 4210,
    description: 'Caches de instaladores antigos, logs de navegadores e relatórios de falhas',
    requiresAdmin: false,
    isCleaned: false
  },
  {
    id: 'win_temp',
    name: 'Arquivos Temporários do Windows',
    path: 'C:\\Windows\\Temp',
    sizeMb: 875.2,
    fileCount: 1680,
    description: 'Arquivos intermediários criados por atualizações do SO e serviços de sistema',
    requiresAdmin: true,
    isCleaned: false
  },
  {
    id: 'win_prefetch',
    name: 'Cache do Windows Prefetch',
    path: 'C:\\Windows\\Prefetch',
    sizeMb: 215.8,
    fileCount: 390,
    description: 'Arquivos .pf de inicialização rápida que se acumulam ao longo do tempo',
    requiresAdmin: true,
    isCleaned: false
  },
  {
    id: 'recycle_bin',
    name: 'Lixeira do Windows ($Recycle.Bin)',
    path: 'C:\\$Recycle.Bin',
    sizeMb: 3450.0,
    fileCount: 24,
    description: 'Itens excluídos retidos nas lixeiras de todas as unidades',
    requiresAdmin: false,
    isCleaned: false
  },
  {
    id: 'win_update_cache',
    name: 'Cache do Windows Update (SoftwareDistribution)',
    path: 'C:\\Windows\\SoftwareDistribution\\Download',
    sizeMb: 2840.0,
    fileCount: 92,
    description: 'Instaladores de patches cumulativos já aplicados que continuam no disco',
    requiresAdmin: true,
    isCleaned: false
  }
];

export const INITIAL_DRIVES: DiskDrive[] = [
  {
    letter: 'C:',
    label: 'Windows-SSD',
    totalGb: 512,
    freeGb: 42.4,
    usedPercent: 91.7,
    smartStatus: 'OK',
    fragmentationPercent: 8,
    isSSD: true
  },
  {
    letter: 'D:',
    label: 'Dados-Storage',
    totalGb: 1024,
    freeGb: 580.0,
    usedPercent: 43.3,
    smartStatus: 'OK',
    fragmentationPercent: 2,
    isSSD: true
  }
];

export const INITIAL_SERVICES: WindowsService[] = [
  {
    name: 'wuauserv',
    displayName: 'Windows Update',
    status: 'Stopped',
    startupType: 'Automatic',
    critical: true,
    description: 'Gerencia o download e instalação de atualizações para o Windows e programas'
  },
  {
    name: 'bits',
    displayName: 'Background Intelligent Transfer Service (BITS)',
    status: 'Stopped',
    startupType: 'Automatic',
    critical: true,
    description: 'Transfere arquivos em segundo plano usando largura de banda ociosa'
  },
  {
    name: 'spooler',
    displayName: 'Spooler de Impressão',
    status: 'Running',
    startupType: 'Automatic',
    critical: false,
    description: 'Carrega arquivos na memória para impressão posterior'
  },
  {
    name: 'WinDefend',
    displayName: 'Microsoft Defender Antivirus',
    status: 'Running',
    startupType: 'Automatic',
    critical: true,
    description: 'Ajuda a proteger os computadores contra malware e outras ameaças potenciais'
  },
  {
    name: 'Dhcp',
    displayName: 'Cliente DHCP',
    status: 'Running',
    startupType: 'Automatic',
    critical: true,
    description: 'Registra e atualiza endereços IP e registros DNS para este computador'
  },
  {
    name: 'Dnscache',
    displayName: 'Cliente DNS',
    status: 'Running',
    startupType: 'Automatic',
    critical: true,
    description: 'Armazena em cache nomes de domínio (DNS) e registra este computador'
  },
  {
    name: 'BFE',
    displayName: 'Base Filtering Engine (Firewall)',
    status: 'Running',
    startupType: 'Automatic',
    critical: true,
    description: 'Gerencia políticas de firewall e segurança de protocolo IP (IPsec)'
  }
];

export function getInitialSystemHealthState(): SystemHealthState {
  const hardwareCores = typeof navigator !== 'undefined' ? (navigator.hardwareConcurrency || 8) : 8;
  const memoryEstimate = typeof navigator !== 'undefined' && (navigator as any).deviceMemory ? (navigator as any).deviceMemory : 16;

  return {
    isAdmin: true, // Default active elevated mode
    lastDiagnosisTime: null,
    cpuUsage: 78.4,
    cpuTempC: 58,
    cpuCores: Math.max(4, Math.floor(hardwareCores / 2)),
    cpuThreads: hardwareCores,
    ramTotalGb: memoryEstimate,
    ramUsedGb: Number((memoryEstimate * 0.84).toFixed(1)),
    ramUsagePercent: 84.0,
    sfcStatus: 'corrupted', // Issues ready for diagnosis and auto-fix demo
    dismStatus: 'corrupted',
    storageCategories: INITIAL_STORAGE_CATEGORIES,
    drives: INITIAL_DRIVES,
    processes: INITIAL_PROCESSES,
    network: {
      pingMs: 82,
      packetLoss: 6,
      jitterMs: 14,
      online: true,
      dnsResolved: true,
      adapters: [
        {
          name: 'Ethernet Intel I225-V 2.5GbE',
          type: 'Ethernet',
          speedMbps: 2500,
          status: 'Up',
          ip: '192.168.1.140'
        },
        {
          name: 'Intel Wi-Fi 6E AX211 160MHz',
          type: 'Wi-Fi',
          speedMbps: 1200,
          status: 'Up',
          ip: '192.168.1.141'
        }
      ]
    },
    services: INITIAL_SERVICES,
    detectedIssues: [
      'Uso elevado de memória RAM (84.0% em uso)',
      'Processo unresponsive_task.exe causando gargalo de CPU (31.8%)',
      'Acúmulo crítico de 8.8 GB em arquivos temporários, Prefetch e Lixeira',
      'Unidade principal C: com menos de 10% de espaço livre (42.4 GB livres)',
      'Violações de integridade detectadas em componentes de sistema (SFC /verifyonly)',
      'Serviço crítico parado: Windows Update (wuauserv)',
      'Serviço crítico parado: Background Intelligent Transfer Service (BITS)',
      'Instabilidade de rede detectada (perda de pacotes de 6% e latência de 82ms)'
    ],
    fixedIssues: [],
    terminalLogs: [
      '[SYSTEM] PC Health Check & Auto-Fix v2.5 carregado com sucesso.',
      '[PRIVILEGE] Verificando privilégios UAC: IsUserAnAdmin() == TRUE (Elevado).',
      '[READY] Pressione "Fase 1: Iniciar Análise" para varrer o sistema ou "Fase 2: Auto-Fix" para reparar problemas.'
    ],
    isDiagnosing: false,
    isFixing: false
  };
}
