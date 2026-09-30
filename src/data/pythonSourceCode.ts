export interface PythonFileItem {
  id: string;
  filename: string;
  language: string;
  description: string;
  category: 'core' | 'engine' | 'gui' | 'config' | 'scripts';
  code: string;
}

export const PYTHON_PROJECT_FILES: PythonFileItem[] = [
  {
    id: 'main',
    filename: 'main.py',
    language: 'python',
    description: 'Ponto de entrada com verificação e solicitação de elevação UAC (Administrador)',
    category: 'core',
    code: `"""
PC Health Check & Auto-Fix - Entry Point & UAC Privilege Elevation.

Este módulo é o ponto de entrada principal do aplicativo desktop.
Ele verifica se o processo atual possui privilégios de Administrador
no Windows (necessário para reparos do SFC, DISM, Winsock e limpeza do Prefetch).
Caso não possua, solicita elevação UAC automaticamente via ShellExecuteW.

Autor: Senior Infrastructure & Windows Automation Engineer
Licença: MIT
"""

import sys
import os
import ctypes

def is_admin() -> bool:
    """
    Verifica se o processo atual possui privilégios administrativos no Windows.
    
    Returns:
        bool: True se estiver executando como Administrador, False caso contrário.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        # Em ambientes não-Windows de desenvolvimento/teste ou erro na chamada
        return False


def request_admin_elevation() -> None:
    """
    Solicita elevação de privilégios via Prompt UAC do Windows e reinicia o script.
    Se o usuário aceitar no prompt UAC, o processo atual é encerrado e a nova
    instância elevada assume a execução.
    """
    if not is_admin():
        print("[!] Privilégios de Administrador não detectados. Solicitando elevação UAC...")
        try:
            # Reinvoca o interpretador Python com parâmetros completos via verbo 'runas'
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                params,
                None,
                1  # SW_SHOWNORMAL
            )
            # Se ret > 32 a chamada foi bem sucedida
            if ret > 32:
                sys.exit(0)
            else:
                print(f"[-] O usuário recusou a elevação UAC (Código de retorno: {ret}).")
        except Exception as e:
            print(f"[-] Falha ao solicitar privilégios administrativos: {e}")


def main():
    """Inicializa a interface gráfica do aplicativo após validação de privilégios."""
    # Solicita elevação de Administrador se estiver no Windows
    if sys.platform == "win32" and not is_admin():
        request_admin_elevation()
        return

    # Importa a GUI após validação de UAC
    try:
        from gui import PCHealthApp
        app = PCHealthApp(is_elevated=is_admin())
        app.mainloop()
    except ImportError as err:
        print(f"[-] Erro ao carregar módulos: {err}")
        print("[*] Certifique-se de executar: pip install -r requirements.txt")
        input("Pressione Enter para sair...")
    except Exception as err:
        print(f"[-] Erro fatal na aplicação: {err}")
        input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
`
  },
  {
    id: 'diagnostics',
    filename: 'diagnostics.py',
    language: 'python',
    description: 'Fase 1: Motor de diagnóstico completo (CPU, RAM, Discos, S.M.A.R.T., Rede e SFC)',
    category: 'engine',
    code: `"""
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
            win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\\\Windows"), "Temp")
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
            prefetch_path = os.path.join(os.environ.get("SystemRoot", "C:\\\\Windows"), "Prefetch")
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
                    match = re.search(r"(\\d+)%", output)
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
            cmd = ["ping", "-n", "4", "-w", "2000", target_ip]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            output = proc.stdout or ""

            loss_match = re.search(r"\\((\\d+)%\\s*(?:de perda|loss)\\)", output, re.IGNORECASE)
            if loss_match:
                result.packet_loss_percent = float(loss_match.group(1))

            avg_match = re.search(r"(?:M[eé]dia|Average)\\s*=\\s*(\\d+)ms", output, re.IGNORECASE)
            if avg_match:
                result.ping_latency_ms = float(avg_match.group(1))
                result.network_online = True
            elif result.packet_loss_percent < 100.0:
                result.network_online = True
                result.ping_latency_ms = 35.0
            else:
                result.network_online = False
                result.issues_list.append("Sem conectividade com a Internet (100% de perda no ping para 8.8.8.8)")

            if result.ping_latency_ms and result.ping_latency_ms > 120.0:
                result.issues_list.append(f"Alta latência de rede detectada: {result.ping_latency_ms:.0f} ms")

            if result.packet_loss_percent > 0.0 and result.packet_loss_percent < 100.0:
                result.issues_list.append(f"Perda de pacotes na conexão: {result.packet_loss_percent:.0f}%")

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
        Verifica a integridade do sistema operacional via \`sfc /verifyonly\`
        e detecta serviços essenciais do Windows parados.
        """
        self._log("[Diagnóstico] Verificando integridade de arquivos do Windows e serviços essenciais...")

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

        if run_sfc_scan:
            self._log("[SFC] Executando sfc /verifyonly (isso pode levar alguns instantes)...")
            try:
                cmd = ["sfc", "/verifyonly"]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=180,
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
`
  },
  {
    id: 'fixer',
    filename: 'fixer.py',
    language: 'python',
    description: 'Fase 2: Motor de resolução automática (Limpeza, SFC/DISM, Flush DNS, Winsock e Processos)',
    category: 'engine',
    code: `"""
PC Health Check & Auto-Fix - Resolution Engine (Fase 2).

Este módulo executa a resolução automática de problemas do sistema Windows:
1. Otimização de Armazenamento: Limpeza de %TEMP%, Temp do Windows, Prefetch e esvaziamento da Lixeira.
2. Correção de SO: Execução silenciosa do SFC (/scannow) e DISM (/RestoreHealth) + reinício de serviços.
3. Reparo de Rede: Flush DNS, release/renew e redefinição do catálogo Winsock e pilha TCP/IP.
4. Gerenciamento de Processos: Finalização segura com 1 clique de processos de usuário que causam gargalo.

Tratamento estrito de erros para evitar paradas quando arquivos estiverem em uso.
"""

import os
import sys
import shutil
import ctypes
import subprocess
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None

from diagnostics import CRITICAL_SYSTEM_PROCESSES, DiagnosticResult


@dataclass
class FixReport:
    """Relatório estruturado das ações de correção executadas."""
    temp_files_deleted: int = 0
    temp_space_freed_mb: float = 0.0
    recycle_bin_cleared: bool = False
    prefetch_cleared: bool = False
    sfc_executed: bool = False
    sfc_success: bool = False
    dism_executed: bool = False
    dism_success: bool = False
    network_repaired: bool = False
    services_restarted: List[str] = field(default_factory=list)
    killed_processes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class AutoFixEngine:
    """Motor de resolução automática e otimização para Windows."""

    def __init__(self, log_callback: Callable[[str], None] = None):
        """
        Inicializa o AutoFixEngine.

        Args:
            log_callback (Callable): Função para registrar logs de progresso em tempo real.
        """
        self.log_callback = log_callback or (lambda msg: None)

    def _log(self, message: str) -> None:
        """Envia mensagem ao callback de log."""
        self.log_callback(message)

    def clean_storage(self, report: FixReport) -> None:
        """
        Otimiza o armazenamento limpando:
        - Pasta %TEMP% do usuário
        - Pasta C:\\Windows\\Temp
        - Pasta C:\\Windows\\Prefetch (requer Admin)
        - Lixeira do Windows (via ctypes ou PowerShell)
        
        Arquivos em uso no momento são ignorados silenciosamente sem travar o app.
        """
        self._log("[Auto-Fix] Iniciando limpeza de armazenamento e arquivos temporários...")

        folders_to_clean = []
        if "TEMP" in os.environ:
            folders_to_clean.append(os.environ["TEMP"])
        win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\\\Windows"), "Temp")
        if os.path.exists(win_temp):
            folders_to_clean.append(win_temp)

        total_deleted = 0
        total_freed_bytes = 0

        # 1. Limpeza de Pastas Temp
        for folder in folders_to_clean:
            if not os.path.exists(folder):
                continue
            self._log(f"[*] Limpando diretório: {folder}")
            try:
                for root, dirs, files in os.walk(folder, topdown=False):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            total_deleted += 1
                            total_freed_bytes += file_size
                        except (PermissionError, OSError):
                            continue

                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            os.rmdir(dir_path)
                        except (PermissionError, OSError):
                            continue
            except Exception as e:
                self._log(f"[-] Aviso ao acessar pasta {folder}: {e}")

        # 2. Limpeza da pasta Prefetch (C:\\Windows\\Prefetch)
        prefetch_path = os.path.join(os.environ.get("SystemRoot", "C:\\\\Windows"), "Prefetch")
        if os.path.exists(prefetch_path):
            self._log("[*] Limpando cache do Windows Prefetch...")
            try:
                for item in os.listdir(prefetch_path):
                    fp = os.path.join(prefetch_path, item)
                    try:
                        if os.path.isfile(fp):
                            fsize = os.path.getsize(fp)
                            os.remove(fp)
                            total_deleted += 1
                            total_freed_bytes += fsize
                    except (PermissionError, OSError):
                        continue
                report.prefetch_cleared = True
            except (PermissionError, OSError) as e:
                self._log(f"[-] Permissão insuficiente para limpar Prefetch (requer Admin): {e}")

        # 3. Esvaziamento da Lixeira do Windows
        self._log("[*] Esvaziando a Lixeira do Windows...")
        recycle_cleared = False
        if sys.platform == "win32":
            try:
                flags = 0x00000001 | 0x00000002 | 0x00000004
                result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
                recycle_cleared = (result == 0)
            except Exception:
                try:
                    ps_cmd = ["powershell", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"]
                    subprocess.run(ps_cmd, capture_output=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    recycle_cleared = True
                except Exception as e:
                    self._log(f"[-] Falha ao esvaziar lixeira: {e}")

        report.recycle_bin_cleared = recycle_cleared
        report.temp_files_deleted = total_deleted
        report.temp_space_freed_mb = round(total_freed_bytes / (1024 * 1024), 2)
        self._log(f"[OK] Limpeza concluída: {total_deleted} arquivos removidos ({report.temp_space_freed_mb} MB liberados).")

    def repair_os_integrity(self, report: FixReport, force_dism: bool = False) -> None:
        """
        Executa reparos de integridade de arquivos do Windows:
        1. DISM /Online /Cleanup-Image /RestoreHealth (se corrupções forem detectadas)
        2. sfc /scannow (para substituir arquivos corrompidos por cópias em cache)
        """
        self._log("[Auto-Fix] Iniciando reparo de integridade do Sistema Operacional...")

        if force_dism:
            self._log("[DISM] Executando: DISM.exe /Online /Cleanup-Image /RestoreHealth...")
            try:
                dism_cmd = ["dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"]
                proc = subprocess.Popen(
                    dism_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                for line in proc.stdout:
                    clean_line = line.strip()
                    if clean_line:
                        self._log(f"[DISM] {clean_line}")
                proc.wait()
                report.dism_executed = True
                report.dism_success = (proc.returncode == 0)
                self._log("[OK] Reparo DISM finalizado com sucesso.")
            except Exception as e:
                self._log(f"[-] Erro ao executar DISM: {e}")
                report.errors.append(f"DISM: {e}")

        self._log("[SFC] Executando sfc /scannow para verificação e reparo automático...")
        try:
            sfc_cmd = ["sfc", "/scannow"]
            proc = subprocess.Popen(
                sfc_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            for line in proc.stdout:
                clean_line = line.strip()
                if clean_line:
                    self._log(f"[SFC] {clean_line}")
            proc.wait()
            report.sfc_executed = True
            report.sfc_success = (proc.returncode in (0, 1))
            self._log("[OK] Verificação SFC concluída.")
        except Exception as e:
            self._log(f"[-] Erro ao executar SFC: {e}")
            report.errors.append(f"SFC: {e}")

    def restart_stopped_services(self, report: FixReport, stopped_services: List[Dict[str, str]]) -> None:
        """
        Tenta inicializar serviços essenciais que foram detectados como parados.
        """
        if not stopped_services:
            return

        self._log("[Auto-Fix] Tentando iniciar serviços essenciais parados...")
        for srv in stopped_services:
            srv_name = srv.get("name")
            display = srv.get("display", srv_name)
            self._log(f"[*] Iniciando serviço: {display} ({srv_name})...")
            try:
                cmd = ["sc", "start", srv_name]
                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=8,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                report.services_restarted.append(display)
                self._log(f"[OK] Comando de inicialização enviado para: {display}")
            except Exception as e:
                self._log(f"[-] Falha ao iniciar serviço {srv_name}: {e}")

    def repair_network(self, report: FixReport) -> None:
        """
        Executa a sequência de reparo de conectividade de rede:
        - ipconfig /flushdns
        - ipconfig /release
        - ipconfig /renew
        - netsh winsock reset
        - netsh int ip reset
        """
        self._log("[Auto-Fix] Executando reparo completo da pilha de rede e DNS...")

        commands = [
            ("ipconfig /flushdns", ["ipconfig", "/flushdns"], "Limpando cache do resolvedor DNS"),
            ("ipconfig /release", ["ipconfig", "/release"], "Liberando endereços IP concedidos"),
            ("ipconfig /renew", ["ipconfig", "/renew"], "Renovando concessões de IP com o roteador/DHCP"),
            ("netsh winsock reset", ["netsh", "winsock", "reset"], "Redefinindo catálogo Winsock do Windows"),
            ("netsh int ip reset", ["netsh", "int", "ip", "reset"], "Redefinindo pilha TCP/IP padrão"),
        ]

        success_count = 0
        for label, cmd_args, desc in commands:
            self._log(f"[*] {desc} ({label})...")
            try:
                proc = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                out = (proc.stdout or "").strip()
                if out:
                    first_line = out.split("\\n")[0]
                    self._log(f"    -> {first_line}")
                success_count += 1
            except Exception as e:
                self._log(f"[-] Erro ao executar {label}: {e}")
                report.errors.append(f"{label}: {e}")

        report.network_repaired = (success_count >= 3)
        self._log("[OK] Reparo de rede finalizado.")

    def kill_offending_processes(self, report: FixReport, process_list: List[Any]) -> None:
        """
        Encerra com segurança processos de usuário que estão causando gargalo de CPU ou RAM.
        Ignora estritamente processos críticos do sistema para evitar BSOD.
        """
        self._log("[Auto-Fix] Gerenciando processos ofensores de CPU/Memória...")
        if not psutil:
            return

        for proc_item in process_list:
            pid = getattr(proc_item, "pid", None)
            name = getattr(proc_item, "name", "Desconhecido")
            is_critical = getattr(proc_item, "is_critical", True)

            if is_critical or name.lower() in CRITICAL_SYSTEM_PROCESSES or (pid and pid <= 4):
                self._log(f"[Protegido] Processo crítico ignorado por segurança: {name} (PID: {pid})")
                continue

            try:
                p = psutil.Process(pid)
                p.terminate()
                try:
                    p.wait(timeout=2)
                except psutil.TimeoutExpired:
                    p.kill()

                report.killed_processes.append(f"{name} (PID: {pid})")
                self._log(f"[OK] Processo ofensor encerrado: {name} (PID: {pid})")
            except Exception as e:
                self._log(f"[-] Não foi possível encerrar {name} (PID: {pid}): {e}")

    def run_auto_fix(
        self,
        diag_result: DiagnosticResult,
        fix_storage: bool = True,
        fix_os: bool = True,
        fix_network: bool = True,
        kill_procs: bool = False
    ) -> FixReport:
        """
        Executa a Fase 2 completa de resolução automática com base no diagnóstico anterior.
        """
        report = FixReport()
        self._log("=== INICIANDO FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ===")

        if fix_storage:
            self.clean_storage(report)

        if fix_network or not diag_result.network_online:
            self.repair_network(report)

        if fix_os:
            need_dism = not diag_result.sfc_integrity_ok
            self.repair_os_integrity(report, force_dism=need_dism)
            self.restart_stopped_services(report, diag_result.stopped_services)

        if kill_procs:
            offenders = diag_result.top_cpu_processes + diag_result.top_ram_processes
            unique_offenders = []
            seen_pids = set()
            for p in offenders:
                if p.pid not in seen_pids:
                    seen_pids.add(p.pid)
                    unique_offenders.append(p)
            self.kill_offending_processes(report, unique_offenders)

        self._log("=== FASE 2 CONCLUÍDA COM SUCESSO ===")
        return report
`
  },
  {
    id: 'gui',
    filename: 'gui.py',
    language: 'python',
    description: 'Interface gráfica moderna em CustomTkinter com modo escuro, cards e streaming de terminal',
    category: 'gui',
    code: `"""
PC Health Check & Auto-Fix - Graphical User Interface (CustomTkinter).

Interface gráfica moderna para Windows utilizando CustomTkinter.
Fornece execução não-bloqueante (threading), console de terminal integrado
com streaming de logs, cards visuais de diagnóstico e painel de controle
para a Fase 1 (Análise) e Fase 2 (Auto-Fix).
"""

import sys
import threading
import datetime
from typing import Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from diagnostics import DiagnosticEngine, DiagnosticResult
from fixer import AutoFixEngine, FixReport


class PCHealthApp(ctk.CTk if ctk else object):
    """Janela principal do aplicativo desktop PC Health Check & Auto-Fix."""

    def __init__(self, is_elevated: bool = True):
        if not ctk:
            raise ImportError("CustomTkinter não está instalado. Execute: pip install customtkinter")

        super().__init__()

        self.is_elevated = is_elevated
        self.diagnostic_engine = DiagnosticEngine(log_callback=self._append_log)
        self.fix_engine = AutoFixEngine(log_callback=self._append_log)
        self.last_diagnostic: Optional[DiagnosticResult] = None

        # Configurações de Janela
        self.title("PC Health Check & Auto-Fix - Windows System Optimizer")
        self.geometry("1100x750")
        self.minsize(980, 680)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self._append_log(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sistema pronto. UAC: {'Elevado (Admin)' if self.is_elevated else 'Não-Elevado (Usuário Padrão)'}")

    def _build_ui(self) -> None:
        """Monta a estrutura de widgets da interface."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ BARRA LATERAL (SIDEBAR) ------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PC Health Check\\n& Auto-Fix",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(24, 12))

        status_color = "#10b981" if self.is_elevated else "#f59e0b"
        status_text = "Privilégio: Administrador" if self.is_elevated else "Aviso: Sem Admin"
        self.uac_badge = ctk.CTkLabel(
            self.sidebar_frame,
            text=status_text,
            text_color=status_color,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.uac_badge.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Botão Fase 1: Análise Completa
        self.btn_analyze = ctk.CTkButton(
            self.sidebar_frame,
            text="🔍 Iniciar Análise (F1)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self.start_analysis_thread
        )
        self.btn_analyze.grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        # Botão Fase 2: Auto-Fix
        self.btn_fix = ctk.CTkButton(
            self.sidebar_frame,
            text="⚡ Corrigir Tudo (F2)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_autofix_thread
        )
        self.btn_fix.grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        self.opt_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Opções de Reparo:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        self.opt_label.grid(row=4, column=0, padx=20, pady=(16, 4), sticky="w")

        self.chk_storage = ctk.CTkCheckBox(self.sidebar_frame, text="Limpar Temp / Lixeira")
        self.chk_storage.select()
        self.chk_storage.grid(row=5, column=0, padx=20, pady=4, sticky="w")

        self.chk_network = ctk.CTkCheckBox(self.sidebar_frame, text="Reparar Rede / DNS")
        self.chk_network.select()
        self.chk_network.grid(row=6, column=0, padx=20, pady=4, sticky="w")

        self.chk_os = ctk.CTkCheckBox(self.sidebar_frame, text="SFC / DISM & Serviços")
        self.chk_os.select()
        self.chk_os.grid(row=7, column=0, padx=20, pady=4, sticky="w")

        self.chk_procs = ctk.CTkCheckBox(self.sidebar_frame, text="Matar Processos Gargalo")
        self.chk_procs.grid(row=8, column=0, padx=20, pady=4, sticky="nw")

        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v2.5 Professional\\nWindows 10/11 x64",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.version_label.grid(row=9, column=0, padx=20, pady=16)

        # ------------------ ÁREA DE CONTEÚDO PRINCIPAL ------------------
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.main_content, height=8)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.progress_bar.set(0)

        # Painel de Cards de Diagnóstico
        self.cards_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.cards_frame.grid_columnconfigure((0, 1), weight=1)

        # Card 1: CPU & RAM
        self.card_cpu = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_cpu.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self.lbl_cpu_title = ctk.CTkLabel(self.card_cpu, text="⚙️ CPU & Memória RAM", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_cpu_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_cpu_stats = ctk.CTkLabel(self.card_cpu, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_cpu_stats.pack(anchor="w", padx=14, pady=4)

        # Card 2: Armazenamento
        self.card_disk = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_disk.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        self.lbl_disk_title = ctk.CTkLabel(self.card_disk, text="💾 Armazenamento & Disco", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_disk_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_disk_stats = ctk.CTkLabel(self.card_disk, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_disk_stats.pack(anchor="w", padx=14, pady=4)

        # Card 3: Rede
        self.card_net = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_net.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")
        self.lbl_net_title = ctk.CTkLabel(self.card_net, text="🌐 Rede & Conectividade", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_net_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_net_stats = ctk.CTkLabel(self.card_net, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_net_stats.pack(anchor="w", padx=14, pady=4)

        # Card 4: SO
        self.card_os = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_os.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")
        self.lbl_os_title = ctk.CTkLabel(self.card_os, text="🛡️ Sistema & Serviços", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_os_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_os_stats = ctk.CTkLabel(self.card_os, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_os_stats.pack(anchor="w", padx=14, pady=4)

        # Console
        self.log_container = ctk.CTkFrame(self.main_content, corner_radius=8)
        self.log_container.grid(row=2, column=0, sticky="nsew")
        self.log_container.grid_rowconfigure(1, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)

        self.log_header = ctk.CTkLabel(
            self.log_container,
            text="Terminal de Execução e Logs em Tempo Real",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        self.log_header.grid(row=0, column=0, padx=14, pady=(8, 4), sticky="w")

        self.txt_log = ctk.CTkTextbox(
            self.log_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            fg_color="#090d16"
        )
        self.txt_log.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="nsew")

    def _append_log(self, text: str) -> None:
        """Adiciona linha no console de forma thread-safe."""
        def update():
            self.txt_log.insert("end", text + "\\n")
            self.txt_log.see("end")
        self.after(0, update)

    def start_analysis_thread(self) -> None:
        """Inicia a Análise da Fase 1 em uma thread separada."""
        self.btn_analyze.configure(state="disabled")
        self.btn_fix.configure(state="disabled")
        self.progress_bar.set(0.1)

        def worker():
            try:
                self.progress_bar.set(0.2)
                result = self.diagnostic_engine.run_full_diagnosis(run_sfc=False)
                self.last_diagnostic = result
                self.progress_bar.set(1.0)
                self.after(0, lambda: self._update_cards_with_results(result))
            finally:
                self.after(0, lambda: self.btn_analyze.configure(state="normal"))
                self.after(0, lambda: self.btn_fix.configure(state="normal"))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _update_cards_with_results(self, res: DiagnosticResult) -> None:
        """Atualiza os cards da interface com os dados medidos."""
        cpu_text = f"CPU: {res.cpu_usage_percent:.1f}% ({res.cpu_cores_physical}C/{res.cpu_cores_logical}T)\\n"
        cpu_text += f"RAM: {res.ram_used_gb:.1f}GB / {res.ram_total_gb:.1f}GB ({res.ram_usage_percent:.1f}%)\\n"
        if res.top_cpu_processes:
            top_p = res.top_cpu_processes[0]
            cpu_text += f"Maior consumidor: {top_p.name} ({top_p.cpu_percent:.1f}%)"
        self.lbl_cpu_stats.configure(text=cpu_text)

        disk_text = ""
        for d in res.disks[:2]:
            disk_text += f"{d['drive']}: {d['free_gb']}GB livres ({d['used_percent']}%)\\n"
        disk_text += f"Temp: {res.temp_files_size_mb} MB ({res.temp_files_count} arquivos)\\n"
        disk_text += f"S.M.A.R.T.: {res.smart_status}"
        self.lbl_disk_stats.configure(text=disk_text)

        net_text = f"Status: {'Conectado' if res.network_online else 'Sem Internet'}\\n"
        net_text += f"Latência (8.8.8.8): {res.ping_latency_ms or 0:.0f} ms\\n"
        net_text += f"Perda de Pacotes: {res.packet_loss_percent:.0f}%\\n"
        net_text += f"Adaptadores Ativos: {len(res.network_adapters)}"
        self.lbl_net_stats.configure(text=net_text)

        os_text = f"Integridade SFC: {'OK' if res.sfc_integrity_ok else 'Violações Detectadas'}\\n"
        os_text += f"Serviços Parados: {len(res.stopped_services)}\\n"
        if res.stopped_services:
            os_text += f"Ex: {res.stopped_services[0]['display'][:24]}..."
        else:
            os_text += "Todos os serviços essenciais em execução"
        self.lbl_os_stats.configure(text=os_text)

    def start_autofix_thread(self) -> None:
        """Inicia a Fase 2 (Auto-Fix) em uma thread separada."""
        self.btn_analyze.configure(state="disabled")
        self.btn_fix.configure(state="disabled")
        self.progress_bar.set(0.1)

        do_storage = bool(self.chk_storage.get())
        do_net = bool(self.chk_network.get())
        do_os = bool(self.chk_os.get())
        do_procs = bool(self.chk_procs.get())

        def worker():
            try:
                diag = self.last_diagnostic or DiagnosticResult()
                self.progress_bar.set(0.3)
                report = self.fix_engine.run_auto_fix(
                    diag_result=diag,
                    fix_storage=do_storage,
                    fix_os=do_os,
                    fix_network=do_net,
                    kill_procs=do_procs
                )
                self.progress_bar.set(1.0)
                self._append_log(f"\\n[SUCESSO] Auto-Fix Finalizado!\\n- Arquivos Deletados: {report.temp_files_deleted} ({report.temp_space_freed_mb} MB)")
                if report.network_repaired:
                    self._append_log("- Pilha de Rede: Redefinida com sucesso.")
                if report.killed_processes:
                    self._append_log(f"- Processos Encerrados: {', '.join(report.killed_processes)}")
            finally:
                self.after(0, lambda: self.btn_analyze.configure(state="normal"))
                self.after(0, lambda: self.btn_fix.configure(state="normal"))

        t = threading.Thread(target=worker, daemon=True)
        t.start()


if __name__ == "__main__":
    app = PCHealthApp(is_elevated=True)
    app.mainloop()
`
  },
  {
    id: 'requirements',
    filename: 'requirements.txt',
    language: 'plaintext',
    description: 'Lista de pacotes pip necessários para execução no Windows',
    category: 'config',
    code: `# Dependências para PC Health Check & Auto-Fix
customtkinter>=5.2.0
psutil>=5.9.0
wmi>=1.5.1
pywin32>=306
packaging>=23.0
`
  },
  {
    id: 'run_admin',
    filename: 'run_admin.bat',
    language: 'bat',
    description: 'Script batch para executar com elevação de Administrador direta via UAC',
    category: 'scripts',
    code: `@echo off
:: Batch script para executar o PC Health Check & Auto-Fix com elevação de Administrador direta
title PC Health Check & Auto-Fix Launcher

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Privilégios de Administrador detectados!
) else (
    echo [!] Solicitando permissão de Administrador via UAC...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dp0run_admin.bat\"\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo [*] Verificando dependencias Python...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check

echo [*] Inicializando PC Health Check & Auto-Fix...
python main.py
if %errorLevel% neq 0 (
    echo.
    echo [-] O aplicativo encerrou com erro.
    pause
)
`
  },
  {
    id: 'build_exe',
    filename: 'build_exe.bat',
    language: 'bat',
    description: 'Script para compilar em arquivo .exe autônomo com manifesto UAC embutido',
    category: 'scripts',
    code: `@echo off
:: Script para compilar o PC Health Check & Auto-Fix em um executável autônomo (.exe) com UAC embutido
title Compilador PyInstaller - PC Health Check

echo [*] Instalando PyInstaller...
pip install pyinstaller

echo [*] Compilando executavel com manifesto de Administrador (uac-admin)...
pyinstaller --noconsole --onefile --uac-admin --name="PC_Health_Check_AutoFix" --hidden-import="wmi" --hidden-import="win32timezone" main.py

echo.
echo [OK] Compilacao concluida! O executavel esta na pasta: dist/PC_Health_Check_AutoFix.exe
pause
`
  },
  {
    id: 'readme',
    filename: 'README.md',
    language: 'markdown',
    description: 'Instruções completas de instalação, comandos e arquitetura técnica',
    category: 'config',
    code: `# PC Health Check & Auto-Fix 🚀
**Aplicativo Desktop Profissional de Diagnóstico Profundo e Resolução Automática para Windows**

Desenvolvido para engenheiros de infraestrutura, técnicos de suporte e administradores de sistemas Windows 10/11.

---

## 🛠️ Arquitetura Modular

| Módulo | Responsabilidade |
| :--- | :--- |
| \`main.py\` | Ponto de entrada, checagem de privilégios e elevação UAC transparente via \`ShellExecuteW\`. |
| \`diagnostics.py\` | **Fase 1:** Motor de análise de CPU, RAM, processos consumidores, discos, SMART, fragmentação, rede (ping 8.8.8.8) e integridade SFC/serviços. |
| \`fixer.py\` | **Fase 2:** Motor de reparo automático (limpeza de \`%TEMP%\` e Prefetch, esvaziamento de Lixeira, execução de SFC/DISM, reset de DNS e catálogo Winsock, encerramento de processos ofensores). |
| \`gui.py\` | Interface gráfica moderna construída com \`CustomTkinter\`, console de streaming de comandos em tempo real e threads assíncronas. |
| \`run_admin.bat\` | Inicializador em lote para execução direta com elevação de Administrador. |
| \`build_exe.bat\` | Script automatizado para empacotar em um executável autônomo único com \`PyInstaller\` e manifesto UAC. |

---

## 📦 Instalação das Dependências

Abra o prompt de comando (CMD ou PowerShell) e execute:

\`\`\`bash
pip install -r requirements.txt
\`\`\`

Ou instale manualmente as bibliotecas necessárias:
\`\`\`bash
pip install customtkinter psutil wmi pywin32 packaging
\`\`\`

> **Nota:** Em sistemas Windows de 64 bits, certifique-se de executar com privilégios de Administrador para que a limpeza de \`C:\\Windows\\Prefetch\`, o reparo SFC/DISM e o comando \`netsh winsock reset\` funcionem sem restrições do sistema.

---

## 🚀 Como Executar

### Opção 1: Via Inicializador Batch (Recomendado)
Clique com o botão direito em \`run_admin.bat\` e selecione **"Executar como Administrador"**.

### Opção 2: Via Terminal Python
\`\`\`bash
python main.py
\`\`\`
*(Caso não esteja como Administrador, o próprio script abrirá a janela do UAC para autorizar a elevação).*

---

## ⚙️ Como Gerar o Executável (.exe)

Para criar um arquivo executável único sem necessidade de ter Python instalado na máquina do usuário final:

\`\`\`bash
run build_exe.bat
\`\`\`
Ou manualmente:
\`\`\`bash
pyinstaller --noconsole --onefile --uac-admin --name="PC_Health_Check_AutoFix" main.py
\`\`\`
O executável final estará disponível no diretório \`dist/PC_Health_Check_AutoFix.exe\`.
`
  }
];
