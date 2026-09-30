export interface ProcessItem {
  pid: number;
  name: string;
  cpu: number; // percentage
  memoryMb: number;
  isCritical: boolean;
  status: 'running' | 'terminated';
  description: string;
}

export interface StorageCategory {
  id: string;
  name: string;
  path: string;
  sizeMb: number;
  fileCount: number;
  description: string;
  requiresAdmin: boolean;
  isCleaned: boolean;
}

export interface DiskDrive {
  letter: string;
  label: string;
  totalGb: number;
  freeGb: number;
  usedPercent: number;
  smartStatus: 'OK' | 'Warning' | 'Failing';
  fragmentationPercent: number;
  isSSD: boolean;
}

export interface NetworkStatus {
  pingMs: number;
  packetLoss: number;
  jitterMs: number;
  online: boolean;
  dnsResolved: boolean;
  adapters: {
    name: string;
    type: 'Ethernet' | 'Wi-Fi' | 'Virtual';
    speedMbps: number;
    status: 'Up' | 'Down';
    ip: string;
  }[];
}

export interface WindowsService {
  name: string;
  displayName: string;
  status: 'Running' | 'Stopped';
  startupType: 'Automatic' | 'Manual' | 'Disabled';
  critical: boolean;
  description: string;
}

export interface SystemHealthState {
  isAdmin: boolean;
  lastDiagnosisTime: string | null;
  cpuUsage: number;
  cpuTempC: number;
  cpuCores: number;
  cpuThreads: number;
  ramTotalGb: number;
  ramUsedGb: number;
  ramUsagePercent: number;
  sfcStatus: 'healthy' | 'corrupted' | 'unverified' | 'repaired';
  dismStatus: 'healthy' | 'corrupted' | 'repaired' | 'unverified';
  storageCategories: StorageCategory[];
  drives: DiskDrive[];
  processes: ProcessItem[];
  network: NetworkStatus;
  services: WindowsService[];
  detectedIssues: string[];
  fixedIssues: string[];
  terminalLogs: string[];
  isDiagnosing: boolean;
  isFixing: boolean;
}
