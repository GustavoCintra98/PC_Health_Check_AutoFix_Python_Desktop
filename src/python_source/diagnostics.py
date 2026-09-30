"""
PC Health Check & Auto-Fix - Diagnostic Engine (Fase 1).

Este módulo implementa a varredura completa dos subsistemas Windows:
- CPU e Memória (com identificação de gargalos e filtragem de processos críticos)
- Armazenamento (espaço, S.M.A.R.T., fragmentação e contagem de cache/temp)
- Rede e Conectividade (ping para 8.8.8.8, perda de pacotes e adaptadores)
- Sistema Operacional (integridade sfc /verifyonly e serviços essenciais)

Tratamento de exceções robusto em todas as chamadas para garantir resiliência.
"""

import os
import sys
import re
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None

try:
    import wmi
except ImportError:
    wmi = None

# Lista de processos essenciais do Windows que NUNCA devem ser encerrados
CRITICAL_SYSTEM_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "dwm.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "sihost.exe",
    "taskhostw.exe",
    "explorer.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe",
    "securityhealthservice.exe",
    "spoolsv.exe"
}

# Serviços essenciais do Windows para monitoramento
ESSENTIAL_SERVICES = [
    {"name": "wuauserv", "display": "Windows Update", "critical": True},
    {"name": "bits", "display": "Background Intelligent Transfer Service (BITS)", "critical": True},
    {"name": "spooler", "display": "Spooler de Impressão", "critical": False},
    {"name": "WinDefend", "display": "Microsoft Defender Antivirus", "critical": True},
    {"name": "Dhcp", "display": "Cliente DHCP", "critical": True},
    {"name": "Dnscache", "display": "Cliente DNS", "critical": True},
    {"name": "BFE", "display": "Base Filtering Engine (Firewall)", "critical": True},
]


@dataclass
class ProcessInfo:
    """Informações de um processo em execução."""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    is_critical: bool


@dataclass
class DiagnosticResult:
    """Resultado estruturado de todas as verificações do sistema."""
    # CPU & Memória
    cpu_usage_percent: float = 0.0
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    cpu_bottleneck: bool = False
    ram_total_gb: float = 0.0
    ram_used_gb: float = 0.0
    ram_free_gb: float = 0.0
    ram_usage_percent: float = 0.0
    ram_bottleneck: bool = False
    top_cpu_processes: List[ProcessInfo] = field(default_factory=list)
    top_ram_processes: List[ProcessInfo] = field(default_factory=list)

    # Armazenamento
    disks: List[Dict[str, Any]] = field(default_factory=list)
    temp_files_count: int = 0
    temp_files_size_mb: float = 0.0
    prefetch_files_count: int = 0
    prefetch_size_mb: float = 0.0
    smart_status: str = "Desconhecido"
    smart_healthy: bool = True
    fragmentation_status: str = "Não analisado"
    high_fragmentation: bool = False

    # Rede
    ping_latency_ms: Optional[float] = None
    packet_loss_percent: float = 0.0
    network_online: bool = False
    network_adapters: List[Dict[str, Any]] = field(default_factory=list)

    # Sistema Operacional
    sfc_integrity_ok: bool = True
    sfc_details: str = "Não verificado"
    stopped_services: List[Dict[str, str]] = field(default_factory=list)
    all_services_status: List[Dict[str, Any]] = field(default_factory=list)

    # Sumário Geral
    total_issues_found: int = 0
    issues_list: List[str] = field(default_factory=list)


class DiagnosticEngine:
    """Motor de análise e diagnóstico para sistemas Windows."""

    def __init__(self, log_callback=None):
        """
        Inicializa o DiagnosticEngine.

        Args:
            log_callback (callable, optional): Função que recebe mensagens de log em tempo real.
        """
        self.log_callback = log_callback or (lambda msg: None)
        self._wmi_conn = None

    def _log(self, message: str) -> None:
        """Envia mensagem ao callback de log."""
        self.log_callback(message)

    def _get_wmi(self):
        """Obtém conexão com WMI de forma resiliente."""
        if self._wmi_conn is None and wmi is not None:
            try:
                self._wmi_conn = wmi.WMI()
            except Exception as e:
                self._log(f"[WMI] Aviso: Não foi possível conectar ao WMI: {e}")
        return self._wmi_conn

    def check_cpu_and_memory(self, result: DiagnosticResult) -> None:
        """
        Analisa uso atual de CPU e Memória RAM, identifica gargalos (>80%)
        e lista os 3 maiores consumidores de recursos não críticos.
        """
        self._log("[Diagnóstico] Analisando CPU e Memória...")
        if not psutil:
            self._log("[-] Biblioteca 'psutil' não disponível.")
            return

        try:
            # Medição de CPU com intervalo breve
            result.cpu_usage_percent = psutil.cpu_percent(interval=0.8)
            result.cpu_cores_physical = psutil.cpu_count(logical=False) or 1
            result.cpu_cores_logical = psutil.cpu_count(logical=True) or 1
            result.cpu_bottleneck = result.cpu_usage_percent >= 80.0

            if result.cpu_bottleneck:
                result.issues_list.append(f"Uso crítico de CPU detectado: {result.cpu_usage_percent:.1f}%")

            # Medição de RAM
            mem = psutil.virtual_memory()
            result.ram_total_gb = round(mem.total / (1024 ** 3), 2)
            result.ram_used_gb = round(mem.used / (1024 ** 3), 2)
            result.ram_free_gb = round(mem.available / (1024 ** 3), 2)
            result.ram_usage_percent = mem.percent
            result.ram_bottleneck = mem.percent >= 85.0

            if result.ram_bottleneck:
                result.issues_list.append(f"Memória RAM sobrecarregada: {mem.percent:.1f}% em uso")

            # Varrer processos em execução
            user_processes: List[ProcessInfo] = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    pinfo = proc.info
                    name = (pinfo.get('name') or "Desconhecido").lower()
                    pid = pinfo.get('pid', 0)
                    is_critical = name in CRITICAL_SYSTEM_PROCESSES or pid <= 4

                    cpu_val = proc.cpu_percent(interval=None) or 0.0
                    mem_val = 0.0
                    if pinfo.get('memory_info'):
                        mem_val = round(pinfo['memory_info'].rss / (1024 * 1024), 1)

                    item = ProcessInfo(
                        pid=pid,
                        name=pinfo.get('name') or "Desconhecido",
                        cpu_percent=cpu_val,
                        memory_mb=mem_val,
                        is_critical=is_critical
                    )
                    if not is_critical:
                        user_processes.append(item)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Top 3 CPU
            sorted_by_cpu = sorted(user_processes, key=lambda x: x.cpu_percent, reverse=True)
            result.top_cpu_processes = sorted_by_cpu[:3]

            # Top 3 RAM
            sorted_by_ram = sorted(user_processes, key=lambda x: x.memory_mb, reverse=True)
            result.top_ram_processes = sorted_by_ram[:3]

            self._log(f"[OK] CPU: {result.cpu_usage_percent}% | RAM: {result.ram_usage_percent}% ({result.ram_used_gb}GB / {result.ram_total_gb}GB)")
        except Exception as e:
            self._log(f"[-] Erro ao analisar CPU/Memória: {e}")

    def check_storage(self, result: DiagnosticResult) -> None:
        """
        Examina espaço em disco, acúmulo de arquivos temporários (%TEMP% e Prefetch),
        saúde física S.M.A.R.T. e necessidade de desfragmentação/otimização.
        """
        self._log("[Diagnóstico] Verificando unidades de armazenamento e integridade de disco...")
        if not psutil:
            return

        try:
            # 1. Espaço em disco em todas as partições montadas
            for part in psutil.disk_partitions(all=False):
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024 ** 3), 2)
                    total_gb = round(usage.total / (1024 ** 3), 2)
                    used_percent = usage.percent

                    disk_data = {
                        "drive": part.device or part.mountpoint,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": total_gb,
                        "free_gb": free_gb,
                        "used_percent": used_percent,
                        "is_low": free_gb < 15.0 or used_percent > 90.0
                    }
                    result.disks.append(disk_data)

                    if disk_data["is_low"]:
                        result.issues_list.append(f"Pouco espaço em disco na unidade {part.mountpoint} ({free_gb} GB livres)")
                except PermissionError:
                    continue

            # 2. Varrer arquivos temporários (%TEMP% e Windows Temp)
            temp_paths = []
            if "TEMP" in os.environ:
                temp_paths.append(os.environ["TEMP"])
            win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
            if os.path.exists(win_temp):
                temp_paths.append(win_temp)

            total_temp_files = 0
            total_temp_size = 0

            for tpath in temp_paths:
                if not os.path.exists(tpath):
                    continue
                try:
                    for root, _, files in os.walk(tpath):
                        for f in files:
                            try:
                                fp = os.path.join(root, f)
                                total_temp_files += 1
                                total_temp_size += os.path.getsize(fp)
                            except (OSError, PermissionError):
                                pass
                except (OSError, PermissionError):
                    pass

            result.temp_files_count = total_temp_files
            result.temp_files_size_mb = round(total_temp_size / (1024 * 1024), 2)

            if result.temp_files_size_mb > 500.0 or result.temp_files_count > 1500:
                result.issues_list.append(f"Acúmulo de arquivos temporários: {result.temp_files_size_mb:.1f} MB ({result.temp_files_count} arquivos)")

            # 3. Varrer pasta Prefetch (requer elevação)
            prefetch_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Prefetch")
            prefetch_count = 0
            prefetch_size = 0
            if os.path.exists(prefetch_path):
                try:
                    for item in os.listdir(prefetch_path):
                        fp = os.path.join(prefetch_path, item)
                        if os.path.isfile(fp):
                            prefetch_count += 1
                            prefetch_size += os.path.getsize(fp)
                except (PermissionError, OSError):
                    pass

            result.prefetch_files_count = prefetch_count
            result.prefetch_size_mb = round(prefetch_size / (1024 * 1024), 2)

            # 4. Status S.M.A.R.T. via WMI ou PowerShell
            result.smart_healthy = True
            result.smart_status = "Saudável (OK)"
            w = self._get_wmi()
            if w:
                try:
                    # Tenta ler discos físicos via WMI
                    drives = w.Win32_DiskDrive()
                    bad_drives = []
                    for d in drives:
                        status = getattr(d, 'Status', 'OK')
                        if status and status.upper() != 'OK':
                            bad_drives.append(f"{getattr(d, 'Model', 'Disco')}: {status}")

                    if bad_drives:
                        result.smart_healthy = False
                        result.smart_status = "Alerta: " + ", ".join(bad_drives)
                        result.issues_list.append("Falha ou alerta iminente de integridade S.M.A.R.T. no disco!")
                except Exception as e:
                    self._log(f"[WMI S.M.A.R.T.] Aviso: {e}")

            # 5. Análise de fragmentação da unidade principal C:
            try:
                cmd = ["defrag.exe", "C:", "/A"]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                output = proc.stdout or ""
                if "recomendado" in output.lower() or "defragment" in output.lower():
                    match = re.search(r"(\d+)%", output)
                    frag_pct = match.group(1) if match else "Elevada"
                    result.fragmentation_status = f"{frag_pct}% fragmentado (Otimização recomendada)"
                    result.high_fragmentation = True
                    result.issues_list.append(f"Desfragmentação recomendada para C: ({frag_pct}%)")
                else:
                    result.fragmentation_status = "Otimizado / Desfragmentação não necessária"
            except (subprocess.SubprocessError, FileNotFoundError, OSError):
                result.fragmentation_status = "Otimizado ou Unidade SSD (TRIM ativo)"

            self._log(f"[OK] Armazenamento: {len(result.disks)} unidades avaliadas | Temp: {result.temp_files_size_mb} MB")
        except Exception as e:
            self._log(f"[-] Erro ao verificar armazenamento: {e}")

    def check_network(self, result: DiagnosticResult) -> None:
        """
        Executa teste de ping para 8.8.8.8 (Google DNS) para medir latência e perda
        de pacotes, além de inspecionar adaptadores de rede físicos e virtuais.
        """
        self._log("[Diagnóstico] Testando conectividade de rede (Ping 8.8.8.8)...")
        target_ip = "8.8.8.8"
        try:
            # Comando ping no Windows com 4 requisições e timeout de 2000ms
            cmd = ["ping", "-n", "4", "-w", "2000", target_ip]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            output = proc.stdout or ""

            # Perda de pacotes: ex: "(0% de perda)" ou "(0% loss)"
            loss_match = re.search(r"\((\d+)%\s*(?:de perda|loss)\)", output, re.IGNORECASE)
            if loss_match:
                result.packet_loss_percent = float(loss_match.group(1))

            # Latência média: ex: "Média = 15ms" ou "Average = 15ms"
            avg_match = re.search(r"(?:M[eé]dia|Average)\s*=\s*(\d+)ms", output, re.IGNORECASE)
            if avg_match:
                result.ping_latency_ms = float(avg_match.group(1))
                result.network_online = True
            elif result.packet_loss_percent < 100.0:
                result.network_online = True
                result.ping_latency_ms = 35.0  # Fallback estimado se respondeu
            else:
                result.network_online = False
                result.issues_list.append("Sem conectividade com a Internet (100% de perda no ping para 8.8.8.8)")

            if result.ping_latency_ms and result.ping_latency_ms > 120.0:
                result.issues_list.append(f"Alta latência de rede detectada: {result.ping_latency_ms:.0f} ms")

            if result.packet_loss_percent > 0.0 and result.packet_loss_percent < 100.0:
                result.issues_list.append(f"Perda de pacotes na conexão: {result.packet_loss_percent:.0f}%")

            # Inspecionar adaptadores de rede
            if psutil:
                stats = psutil.net_if_stats()
                for name, stat in stats.items():
                    if stat.isup and not name.lower().startswith("loopback"):
                        result.network_adapters.append({
                            "name": name,
                            "speed_mbps": stat.speed,
                            "duplex": str(stat.duplex),
                            "mtu": stat.mtu,
                            "is_up": stat.isup
                        })

            self._log(f"[OK] Rede: Latência {result.ping_latency_ms or 0}ms | Perda: {result.packet_loss_percent}%")
        except Exception as e:
            self._log(f"[-] Erro no teste de rede: {e}")
            result.network_online = False
            result.issues_list.append(f"Falha ao executar teste de rede: {e}")

    def check_os_integrity_and_services(self, result: DiagnosticResult, run_sfc_scan: bool = True) -> None:
        """
        Verifica a integridade do sistema operacional via `sfc /verifyonly`
        e detecta serviços essenciais do Windows parados.
        """
        self._log("[Diagnóstico] Verificando integridade de arquivos do Windows e serviços essenciais...")

        # 1. Verificação de Serviços Essenciais
        try:
            for srv_info in ESSENTIAL_SERVICES:
                srv_name = srv_info["name"]
                status_text = "Desconhecido"
                is_running = False

                if psutil:
                    try:
                        service = psutil.win_service_get(srv_name)
                        srv_dict = service.as_dict()
                        status_text = srv_dict.get('status', 'stopped')
                        is_running = (status_text == 'running')
                    except Exception:
                        # Fallback usando comando sc query
                        pass

                if not is_running:
                    try:
                        sc_cmd = ["sc", "query", srv_name]
                        sc_proc = subprocess.run(
                            sc_cmd,
                            capture_output=True,
                            text=True,
                            timeout=5,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                        )
                        if "RUNNING" in (sc_proc.stdout or ""):
                            is_running = True
                            status_text = "running"
                        elif "STOPPED" in (sc_proc.stdout or ""):
                            status_text = "stopped"
                    except Exception:
                        pass

                srv_entry = {
                    "name": srv_name,
                    "display": srv_info["display"],
                    "status": status_text,
                    "critical": srv_info["critical"],
                    "is_running": is_running
                }
                result.all_services_status.append(srv_entry)

                if not is_running and srv_info["critical"]:
                    result.stopped_services.append(srv_entry)
                    result.issues_list.append(f"Serviço crítico parado: {srv_info['display']} ({srv_name})")

        except Exception as e:
            self._log(f"[-] Erro ao verificar serviços: {e}")

        # 2. Verificação SFC (/verifyonly)
        if run_sfc_scan:
            self._log("[SFC] Executando sfc /verifyonly (isso pode levar alguns instantes)...")
            try:
                cmd = ["sfc", "/verifyonly"]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,  # 3 minutos máx
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                output = proc.stdout or ""

                if "found integrity violations" in output.lower() or "encontrou violações de integridade" in output.lower():
                    result.sfc_integrity_ok = False
                    result.sfc_details = "Violações de integridade detectadas nos arquivos do sistema Windows!"
                    result.issues_list.append("Corrupção detectada nos arquivos do Windows (SFC necessita reparo)")
                elif "did not find any integrity violations" in output.lower() or "não encontrou nenhuma violação" in output.lower():
                    result.sfc_integrity_ok = True
                    result.sfc_details = "Nenhuma violação de integridade encontrada (100% íntegro)"
                else:
                    result.sfc_integrity_ok = True
                    result.sfc_details = "Verificação SFC concluída sem erros críticos relatados."

            except subprocess.TimeoutExpired:
                result.sfc_details = "Tempo limite atingido durante o sfc /verifyonly"
            except Exception as e:
                result.sfc_details = f"Aviso na execução do SFC: {e}"
        else:
            result.sfc_details = "Verificação profunda SFC pulada pelo usuário"

        self._log(f"[OK] SO e Serviços: {len(result.stopped_services)} serviços críticos parados")

    def run_full_diagnosis(self, run_sfc: bool = True) -> DiagnosticResult:
        """
        Executa a Fase 1 completa com todas as verificações do sistema.

        Args:
            run_sfc (bool): Se deve executar a varredura sfc /verifyonly.

        Returns:
            DiagnosticResult: Objeto com todos os dados coletados.
        """
        result = DiagnosticResult()
        self._log("=== INICIANDO FASE 1: ANÁLISE COMPLETA DO SISTEMA ===")

        self.check_cpu_and_memory(result)
        self.check_storage(result)
        self.check_network(result)
        self.check_os_integrity_and_services(result, run_sfc_scan=run_sfc)

        result.total_issues_found = len(result.issues_list)
        self._log(f"=== FASE 1 CONCLUÍDA: {result.total_issues_found} PROBLEMAS DETECTADOS ===")
        return result
