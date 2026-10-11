"""
PC Health Check & Auto-Fix - Diagnostic Engine (Fase 1).

Este módulo implementa a varredura completa dos subsistemas Windows:
- CPU e Memória (amostragem real por processo e identificação de gargalos)
- Armazenamento (espaço, saúde dos discos via WMI, tipo de mídia e fragmentação)
- Rede e Conectividade (ping 8.8.8.8 com fallback TCP, perda de pacotes, DNS)
- Sistema Operacional (saúde da imagem via DISM, SFC opcional e serviços essenciais)

Princípio: nenhum valor é inventado. Quando algo não pode ser medido o campo
fica como None / "Desconhecido" e a interface exibe "N/D".
"""

import datetime
import os
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import psutil
except ImportError:
    psutil = None

try:
    import wmi
except ImportError:
    wmi = None

from utils import (
    SFC_ENCODING, com_initialized, get_protected_paths, get_temp_dirs,
    iter_old_files, run_cmd, run_powershell,
)

# Lista de processos essenciais do Windows que NUNCA devem ser encerrados
CRITICAL_SYSTEM_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "memory compression",
    "secure system",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "lsaiso.exe",
    "winlogon.exe",
    "dwm.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "sihost.exe",
    "taskhostw.exe",
    "explorer.exe",
    "conhost.exe",
    "ctfmon.exe",
    "audiodg.exe",
    "msmpeng.exe",
    "nissrv.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "searchhost.exe",
    "searchindexer.exe",
    "securityhealthservice.exe",
    "spoolsv.exe",
    "trustedinstaller.exe",
    "tiworker.exe",
}

# Serviços essenciais do Windows para monitoramento.
# Observação: wuauserv e BITS têm inicialização manual (por gatilho) e ficam
# parados quando ociosos, o que é normal. Só é problema se estiverem desativados.
ESSENTIAL_SERVICES = [
    {"name": "wuauserv", "display": "Windows Update", "critical": True},
    {"name": "bits", "display": "Background Intelligent Transfer Service (BITS)", "critical": True},
    {"name": "spooler", "display": "Spooler de Impressão", "critical": False},
    {"name": "WinDefend", "display": "Microsoft Defender Antivirus", "critical": True},
    {"name": "Dhcp", "display": "Cliente DHCP", "critical": True},
    {"name": "Dnscache", "display": "Cliente DNS", "critical": True},
    {"name": "BFE", "display": "Base Filtering Engine (Firewall)", "critical": True},
]

# Limites de gargalo
CPU_BOTTLENECK_PERCENT = 80.0
RAM_BOTTLENECK_PERCENT = 85.0
# Um processo só é considerado "ofensor" se, durante um gargalo, consumir ao menos:
OFFENDER_CPU_PERCENT = 15.0      # % da CPU total (normalizado como no Gerenciador de Tarefas)
OFFENDER_RAM_PERCENT = 10.0      # % da RAM total

# Arquivos temporários mais novos que isso são ignorados (podem estar em uso por instaladores)
TEMP_MIN_AGE_HOURS = 24.0

# Fragmentação acima deste valor recomenda otimização (mesmo critério do defrag.exe)
FRAGMENTATION_THRESHOLD_PERCENT = 10

# Códigos numéricos da classe MSFT_PhysicalDisk (independentes de idioma)
MEDIA_TYPES = {0: "Não especificado", 3: "HDD", 4: "SSD", 5: "SCM"}
HEALTH_STATUS = {0: "Saudável", 1: "Alerta", 2: "Falha", 5: "Desconhecido"}

PING_TARGET = "8.8.8.8"
TCP_PROBES = [("8.8.8.8", 53), ("1.1.1.1", 443)]
DNS_PROBE_HOST = "www.microsoft.com"


@dataclass
class ProcessInfo:
    """Informações de um processo em execução."""
    pid: int
    name: str
    cpu_percent: float          # % da CPU total (0-100)
    memory_mb: float
    memory_percent: float
    is_critical: bool
    create_time: float = 0.0    # usado para garantir que o PID não foi reutilizado


@dataclass
class DiagnosticResult:
    """Resultado estruturado de todas as verificações do sistema."""
    analyzed_at: Optional[datetime.datetime] = None
    elevated: bool = False

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
    offending_processes: List[ProcessInfo] = field(default_factory=list)

    # Armazenamento
    disks: List[Dict[str, Any]] = field(default_factory=list)
    physical_disks: List[Dict[str, Any]] = field(default_factory=list)
    system_drive_media: str = "Desconhecido"
    temp_files_count: int = 0
    temp_files_size_mb: float = 0.0
    smart_status: str = "Desconhecido"
    smart_healthy: Optional[bool] = None
    fragmentation_status: str = "Não analisado"
    high_fragmentation: bool = False

    # Rede
    ping_latency_ms: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    latency_method: str = ""
    network_online: bool = False
    dns_ok: Optional[bool] = None
    network_adapters: List[Dict[str, Any]] = field(default_factory=list)

    # Sistema Operacional
    image_health: Optional[str] = None          # Healthy / Repairable / NonRepairable (DISM)
    sfc_integrity_ok: Optional[bool] = None     # None = não verificado
    sfc_details: str = "Não verificado"
    third_party_antivirus: List[str] = field(default_factory=list)
    stopped_services: List[Dict[str, Any]] = field(default_factory=list)
    all_services_status: List[Dict[str, Any]] = field(default_factory=list)

    # Sumário Geral
    total_issues_found: int = 0
    issues_list: List[str] = field(default_factory=list)

    @property
    def network_healthy(self) -> bool:
        """Rede online, DNS funcionando, sem perda de pacotes e latência aceitável."""
        return (
            self.network_online
            and self.dns_ok is not False
            and not (self.packet_loss_percent or 0)
            and (self.ping_latency_ms is None or self.ping_latency_ms <= 120.0)
        )


# ---------------------------------------------------------------------------
# Parsers puros (testáveis sem Windows)
# ---------------------------------------------------------------------------

_PING_LOSS_RE = re.compile(r"\((\d+)%")
# "Mínimo = 9ms, Máximo = 12ms, Média = 10ms" / "Minimum = 9ms, Maximum = 12ms, Average = 10ms"
# A ordem mín/máx/média é a mesma em todos os idiomas, então pegamos o 3º valor.
_PING_STATS_RE = re.compile(r"=\s*(\d+)\s*ms\s*,[^=]+=\s*(\d+)\s*ms\s*,[^=]+=\s*(\d+)\s*ms", re.IGNORECASE)


def parse_ping_output(output: str) -> Tuple[Optional[float], Optional[float]]:
    """Extrai (latência média em ms, % de perda) da saída do ping do Windows."""
    loss = None
    loss_match = _PING_LOSS_RE.search(output)
    if loss_match:
        loss = float(loss_match.group(1))
    latency = None
    stats_match = _PING_STATS_RE.search(output)
    if stats_match:
        latency = float(stats_match.group(3))
    return latency, loss


def parse_sfc_output(output: str) -> Optional[str]:
    """
    Interpreta a saída do sfc (/scannow ou /verifyonly) em pt-BR ou inglês.

    Returns:
        "ok", "repaired", "unrepairable", "violations" ou None (não determinado).
    """
    text = output.lower()
    if "unable to fix" in text or re.search(r"n[ãa]o (p[ôo]de|conseguiu) (corrigir|reparar)", text):
        return "unrepairable"
    if "successfully repaired" in text or re.search(r"reparou[\w-]*\s+com\s+[êe]xito", text):
        return "repaired"
    if "did not find any integrity violations" in text or re.search(r"n[ãa]o encontrou (nenhuma )?viola", text):
        return "ok"
    if "found integrity violations" in text or "encontrou viola" in text or "encontrou arquivos corrompidos" in text:
        return "violations"
    return None


_FRAG_RE = re.compile(r"fragment\w*[^=\n]*=\s*(\d+)\s*%", re.IGNORECASE)


def parse_defrag_output(output: str) -> Optional[int]:
    """Extrai o percentual total de fragmentação da saída de `defrag X: /A`."""
    matches = _FRAG_RE.findall(output)
    return int(matches[-1]) if matches else None


def classify_service(status: str, start_type: str) -> Optional[str]:
    """
    Decide se um serviço essencial está em estado problemático.

    Returns:
        Descrição do problema ou None se o estado for normal.
        Serviço manual parado é normal (inicia sob demanda).
    """
    if start_type == "disabled":
        return "desativado"
    if start_type == "automatic" and status != "running":
        return "parado (início automático)"
    return None


def select_offenders(
    processes: List[ProcessInfo],
    cpu_bottleneck: bool,
    ram_bottleneck: bool,
) -> List[ProcessInfo]:
    """Seleciona processos que de fato causam o gargalo detectado (nunca críticos)."""
    offenders: Dict[int, ProcessInfo] = {}
    candidates = [p for p in processes if not p.is_critical]
    if cpu_bottleneck:
        for p in sorted(candidates, key=lambda x: x.cpu_percent, reverse=True)[:3]:
            if p.cpu_percent >= OFFENDER_CPU_PERCENT:
                offenders[p.pid] = p
    if ram_bottleneck:
        for p in sorted(candidates, key=lambda x: x.memory_percent, reverse=True)[:3]:
            if p.memory_percent >= OFFENDER_RAM_PERCENT:
                offenders[p.pid] = p
    return list(offenders.values())


def own_process_tree_pids() -> set:
    """PIDs do próprio aplicativo e de seus processos pai (nunca devem ser encerrados)."""
    pids = {os.getpid()}
    if psutil:
        try:
            pids.update(p.pid for p in psutil.Process().parents())
        except psutil.Error:
            pass
    return pids


def check_internet_tcp(timeout: float = 3.0) -> Optional[float]:
    """Testa conectividade via TCP (funciona mesmo com ICMP bloqueado). Retorna latência em ms ou None."""
    for host, port in TCP_PROBES:
        start = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return round((time.perf_counter() - start) * 1000, 1)
        except OSError:
            continue
    return None


def check_dns(host: str = DNS_PROBE_HOST) -> bool:
    try:
        socket.getaddrinfo(host, 443)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Motor de diagnóstico
# ---------------------------------------------------------------------------

class DiagnosticEngine:
    """Motor de análise e diagnóstico para sistemas Windows."""

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ):
        """
        Args:
            log_callback: Recebe mensagens de log em tempo real.
            progress_callback: Recebe (etapa_atual, total_etapas, descrição).
        """
        self.log_callback = log_callback or (lambda msg: None)
        self.progress_callback = progress_callback or (lambda i, n, label: None)
        self._wmi_cache: Dict[str, Any] = {}

    def _log(self, message: str) -> None:
        self.log_callback(message)

    def _get_wmi(self, namespace: str = "root/cimv2"):
        """
        Conexão WMI válida apenas durante a execução atual (mesma thread).
        O cache é limpo ao final de run_full_diagnosis, antes do CoUninitialize.
        """
        if wmi is None:
            return None
        if namespace not in self._wmi_cache:
            try:
                self._wmi_cache[namespace] = wmi.WMI(namespace=namespace)
            except Exception as e:
                self._log(f"[WMI] Aviso: não foi possível conectar a {namespace}: {e}")
                self._wmi_cache[namespace] = None
        return self._wmi_cache[namespace]

    # ------------------------------------------------------------------ CPU/RAM

    def check_cpu_and_memory(self, result: DiagnosticResult) -> None:
        """
        Mede CPU e RAM e identifica processos que realmente causam gargalo.

        O uso de CPU por processo exige duas leituras: a primeira chamada de
        Process.cpu_percent() sempre retorna 0.0, então fazemos uma amostragem
        de 1 segundo entre as duas.
        """
        self._log("[Diagnóstico] Analisando CPU e Memória...")
        if not psutil:
            self._log("[-] Biblioteca 'psutil' não disponível.")
            return

        try:
            procs = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    proc.cpu_percent(interval=None)  # 1ª leitura (referência)
                    procs.append(proc)
                except psutil.Error:
                    continue

            # Janela de amostragem de 1s (serve também para a CPU total)
            result.cpu_usage_percent = psutil.cpu_percent(interval=1.0)
            result.cpu_cores_physical = psutil.cpu_count(logical=False) or 1
            result.cpu_cores_logical = psutil.cpu_count(logical=True) or 1
            result.cpu_bottleneck = result.cpu_usage_percent >= CPU_BOTTLENECK_PERCENT
            if result.cpu_bottleneck:
                result.issues_list.append(f"Uso crítico de CPU detectado: {result.cpu_usage_percent:.1f}%")

            mem = psutil.virtual_memory()
            result.ram_total_gb = round(mem.total / (1024 ** 3), 2)
            result.ram_used_gb = round(mem.used / (1024 ** 3), 2)
            result.ram_free_gb = round(mem.available / (1024 ** 3), 2)
            result.ram_usage_percent = mem.percent
            result.ram_bottleneck = mem.percent >= RAM_BOTTLENECK_PERCENT
            if result.ram_bottleneck:
                result.issues_list.append(f"Memória RAM sobrecarregada: {mem.percent:.1f}% em uso")

            own_pids = own_process_tree_pids()
            infos: List[ProcessInfo] = []
            for proc in procs:
                try:
                    with proc.oneshot():
                        name = proc.info.get("name") or "Desconhecido"
                        pid = proc.pid
                        rss = proc.memory_info().rss
                        info = ProcessInfo(
                            pid=pid,
                            name=name,
                            cpu_percent=round(proc.cpu_percent(interval=None) / result.cpu_cores_logical, 1),
                            memory_mb=round(rss / (1024 * 1024), 1),
                            memory_percent=round(rss / mem.total * 100, 1),
                            is_critical=(name.lower() in CRITICAL_SYSTEM_PROCESSES or pid <= 4 or pid in own_pids),
                            create_time=proc.create_time(),
                        )
                    infos.append(info)
                except psutil.Error:
                    continue

            user_procs = [p for p in infos if not p.is_critical]
            result.top_cpu_processes = sorted(user_procs, key=lambda x: x.cpu_percent, reverse=True)[:3]
            result.top_ram_processes = sorted(user_procs, key=lambda x: x.memory_mb, reverse=True)[:3]
            result.offending_processes = select_offenders(infos, result.cpu_bottleneck, result.ram_bottleneck)

            self._log(f"[OK] CPU: {result.cpu_usage_percent}% | RAM: {result.ram_usage_percent}% "
                      f"({result.ram_used_gb}GB / {result.ram_total_gb}GB)")
        except Exception as e:
            self._log(f"[-] Erro ao analisar CPU/Memória: {e}")

    # ------------------------------------------------------------ Armazenamento

    def check_storage(self, result: DiagnosticResult) -> None:
        """
        Examina espaço em disco, arquivos temporários elegíveis para limpeza,
        saúde física dos discos e necessidade de desfragmentação.
        """
        self._log("[Diagnóstico] Verificando unidades de armazenamento e integridade de disco...")
        if psutil:
            self._check_disk_space(result)
        self._check_temp_files(result)
        self._check_physical_disks(result)
        self._check_fragmentation(result)
        self._log(f"[OK] Armazenamento: {len(result.disks)} unidades avaliadas | "
                  f"Temp elegível: {result.temp_files_size_mb} MB | Disco do sistema: {result.system_drive_media}")

    def _check_disk_space(self, result: DiagnosticResult) -> None:
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in part.opts or part.fstype == "":
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except OSError:
                continue
            free_gb = round(usage.free / (1024 ** 3), 2)
            disk_data = {
                "drive": part.device or part.mountpoint,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "free_gb": free_gb,
                "used_percent": usage.percent,
                "is_low": free_gb < 15.0 or usage.percent > 90.0,
            }
            result.disks.append(disk_data)
            if disk_data["is_low"]:
                result.issues_list.append(f"Pouco espaço em disco na unidade {part.mountpoint} ({free_gb} GB livres)")

    def _check_temp_files(self, result: DiagnosticResult) -> None:
        """Conta apenas o que a limpeza realmente removeria (mesmos critérios do fixer)."""
        protected = get_protected_paths()
        count, size = 0, 0
        for tpath in get_temp_dirs():
            for _, fsize in iter_old_files(tpath, TEMP_MIN_AGE_HOURS, protected):
                count += 1
                size += fsize
        result.temp_files_count = count
        result.temp_files_size_mb = round(size / (1024 * 1024), 2)
        if result.temp_files_size_mb > 500.0 or result.temp_files_count > 1500:
            result.issues_list.append(
                f"Acúmulo de arquivos temporários: {result.temp_files_size_mb:.1f} MB ({result.temp_files_count} arquivos)")

    def _check_physical_disks(self, result: DiagnosticResult) -> None:
        """Saúde dos discos via MSFT_PhysicalDisk (+ predição de falha S.M.A.R.T. se Admin)."""
        storage = self._get_wmi("root/Microsoft/Windows/Storage")
        if not storage:
            return
        try:
            disks = storage.MSFT_PhysicalDisk()
            for d in disks:
                result.physical_disks.append({
                    "name": d.FriendlyName,
                    "device_id": str(d.DeviceId),
                    "media": MEDIA_TYPES.get(d.MediaType, "Desconhecido"),
                    "health": HEALTH_STATUS.get(d.HealthStatus, "Desconhecido"),
                })

            system_letter = os.environ.get("SystemDrive", "C:")[0].upper()
            for part in storage.MSFT_Partition():
                letter = part.DriveLetter
                letter = chr(letter) if isinstance(letter, int) and letter else (letter or "")
                if letter.upper() == system_letter:
                    for pd in result.physical_disks:
                        if pd["device_id"] == str(part.DiskNumber):
                            result.system_drive_media = pd["media"]
                    break
        except Exception as e:
            self._log(f"[WMI Storage] Aviso: {e}")
            return

        failure_predicted = []
        smart = self._get_wmi("root/wmi") if result.elevated else None
        if smart:
            try:
                for st in smart.MSStorageDriver_FailurePredictStatus():
                    if st.PredictFailure:
                        failure_predicted.append(st.InstanceName)
            except Exception:
                pass  # nem todo controlador (ex.: NVMe via alguns drivers) expõe esta classe

        bad = [f"{d['name']}: {d['health']}" for d in result.physical_disks if d["health"] in ("Alerta", "Falha")]
        if bad or failure_predicted:
            result.smart_healthy = False
            result.smart_status = "Alerta: " + ", ".join(bad + [f"predição de falha ({x})" for x in failure_predicted])
            result.issues_list.append("Alerta de integridade física (S.M.A.R.T.) em disco — faça backup!")
        elif result.physical_disks and all(d["health"] == "Saudável" for d in result.physical_disks):
            result.smart_healthy = True
            result.smart_status = f"Saudável ({len(result.physical_disks)} disco(s))"

    def _check_fragmentation(self, result: DiagnosticResult) -> None:
        if result.system_drive_media == "SSD":
            result.fragmentation_status = "SSD — desfragmentação não se aplica (TRIM)"
            return
        if result.system_drive_media != "HDD":
            result.fragmentation_status = "Não analisado (tipo de disco desconhecido)"
            return
        if not result.elevated:
            result.fragmentation_status = "Não analisado (requer Administrador)"
            return
        drive = os.environ.get("SystemDrive", "C:")
        res = run_cmd(["defrag.exe", drive, "/A"], timeout=120)
        frag = parse_defrag_output(res.output)
        if frag is None:
            result.fragmentation_status = f"Não analisado ({res.error or 'saída não reconhecida'})"
        elif frag >= FRAGMENTATION_THRESHOLD_PERCENT:
            result.high_fragmentation = True
            result.fragmentation_status = f"{frag}% fragmentado (otimização recomendada)"
            result.issues_list.append(f"Desfragmentação recomendada para {drive} ({frag}%)")
        else:
            result.fragmentation_status = f"{frag}% fragmentado (OK)"

    # --------------------------------------------------------------------- Rede

    def check_network(self, result: DiagnosticResult) -> None:
        """
        Ping para 8.8.8.8 (latência e perda). Se o ICMP estiver bloqueado,
        usa conexão TCP como fallback. Também verifica resolução DNS.
        """
        self._log(f"[Diagnóstico] Testando conectividade de rede (Ping {PING_TARGET})...")
        try:
            res = run_cmd(["ping", "-n", "4", "-w", "2000", PING_TARGET], timeout=20)
            latency, loss = parse_ping_output(res.output)
            result.packet_loss_percent = loss

            if latency is not None:
                result.ping_latency_ms = latency
                result.latency_method = "ICMP"
                result.network_online = True
            else:
                tcp_ms = check_internet_tcp()
                if tcp_ms is not None:
                    result.network_online = True
                    result.ping_latency_ms = tcp_ms
                    result.latency_method = "TCP (ICMP bloqueado)"
                    result.packet_loss_percent = None  # perda medida pelo ping não é confiável neste caso
                else:
                    result.network_online = False
                    result.issues_list.append("Sem conectividade com a Internet (ping e TCP falharam)")

            if result.network_online:
                result.dns_ok = check_dns()
                if not result.dns_ok:
                    result.issues_list.append("Internet acessível por IP, mas a resolução de nomes (DNS) falhou")

            if result.ping_latency_ms is not None and result.ping_latency_ms > 120.0:
                result.issues_list.append(f"Alta latência de rede detectada: {result.ping_latency_ms:.0f} ms")
            if result.packet_loss_percent and result.packet_loss_percent < 100.0:
                result.issues_list.append(f"Perda de pacotes na conexão: {result.packet_loss_percent:.0f}%")

            if psutil:
                for name, stat in psutil.net_if_stats().items():
                    if stat.isup and not name.lower().startswith("loopback"):
                        result.network_adapters.append({
                            "name": name,
                            "speed_mbps": stat.speed,
                            "duplex": str(stat.duplex),
                            "mtu": stat.mtu,
                            "is_up": stat.isup,
                        })

            latency_txt = f"{result.ping_latency_ms:.0f}ms ({result.latency_method})" if result.ping_latency_ms is not None else "N/D"
            loss_txt = f"{result.packet_loss_percent:.0f}%" if result.packet_loss_percent is not None else "N/D"
            self._log(f"[OK] Rede: Latência {latency_txt} | Perda: {loss_txt} | DNS: "
                      f"{'OK' if result.dns_ok else 'falhou' if result.dns_ok is False else 'N/D'}")
        except Exception as e:
            self._log(f"[-] Erro no teste de rede: {e}")
            result.issues_list.append(f"Falha ao executar teste de rede: {e}")

    # ---------------------------------------------------------------- SO / Serviços

    def _third_party_antivirus(self) -> List[str]:
        """Antivírus de terceiros registrados na Central de Segurança (WinDefend fica parado nesse caso)."""
        sec = self._get_wmi("root/SecurityCenter2")
        if not sec:
            return []
        try:
            return [a.displayName for a in sec.AntiVirusProduct() if "defender" not in (a.displayName or "").lower()]
        except Exception:
            return []

    @staticmethod
    def _service_state(name: str) -> Tuple[str, str]:
        """Retorna (status, start_type) no formato do psutil, com fallback para `sc`."""
        if psutil:
            try:
                svc = psutil.win_service_get(name)
                return svc.status(), svc.start_type()
            except Exception:
                pass
        # Os tokens RUNNING/AUTO_START etc. do sc.exe não são traduzidos
        status, start_type = "unknown", "unknown"
        q = run_cmd(["sc", "query", name], timeout=10).output
        if "RUNNING" in q:
            status = "running"
        elif "STOPPED" in q:
            status = "stopped"
        qc = run_cmd(["sc", "qc", name], timeout=10).output
        if "AUTO_START" in qc:
            start_type = "automatic"
        elif "DEMAND_START" in qc:
            start_type = "manual"
        elif "DISABLED" in qc:
            start_type = "disabled"
        return status, start_type

    def check_os_integrity_and_services(self, result: DiagnosticResult, run_sfc_scan: bool = False) -> None:
        """
        Verifica serviços essenciais, saúde da imagem do Windows (DISM CheckHealth,
        rápido) e, opcionalmente, `sfc /verifyonly` (lento: 5-15 min).
        """
        self._log("[Diagnóstico] Verificando integridade do Windows e serviços essenciais...")

        result.third_party_antivirus = self._third_party_antivirus()
        for srv_info in ESSENTIAL_SERVICES:
            srv_name = srv_info["name"]
            status, start_type = self._service_state(srv_name)
            problem = classify_service(status, start_type)

            if srv_name == "WinDefend" and result.third_party_antivirus:
                problem = None  # Defender fica inativo por design quando há outro antivírus

            srv_entry = {
                "name": srv_name,
                "display": srv_info["display"],
                "status": status,
                "start_type": start_type,
                "critical": srv_info["critical"],
                "is_running": status == "running",
                "problem": problem,
            }
            result.all_services_status.append(srv_entry)
            if problem and srv_info["critical"]:
                result.stopped_services.append(srv_entry)
                result.issues_list.append(f"Serviço essencial {problem}: {srv_info['display']} ({srv_name})")

        if result.third_party_antivirus:
            self._log(f"[*] Antivírus de terceiros detectado: {', '.join(result.third_party_antivirus)}")

        if result.elevated:
            self._log("[DISM] Verificando saúde da imagem do Windows (CheckHealth)...")
            res = run_powershell("(Repair-WindowsImage -Online -CheckHealth).ImageHealthState", timeout=180)
            state = res.output.strip().splitlines()[-1].strip() if res.ok and res.output.strip() else None
            if state in ("Healthy", "Repairable", "NonRepairable"):
                result.image_health = state
                if state != "Healthy":
                    result.issues_list.append(f"Imagem do Windows com problemas (DISM: {state})")
            else:
                self._log(f"[-] Não foi possível obter a saúde da imagem: {res.error or res.output[-200:]}")
        else:
            self._log("[*] Verificação DISM ignorada (requer Administrador).")

        if run_sfc_scan and result.elevated:
            self._log("[SFC] Executando sfc /verifyonly (pode levar de 5 a 15 minutos)...")
            res = run_cmd(["sfc", "/verifyonly"], timeout=1800, encoding=SFC_ENCODING)
            verdict = parse_sfc_output(res.output)
            if verdict == "ok":
                result.sfc_integrity_ok = True
                result.sfc_details = "Nenhuma violação de integridade encontrada"
            elif verdict in ("violations", "repaired", "unrepairable"):
                result.sfc_integrity_ok = False
                result.sfc_details = "Violações de integridade detectadas nos arquivos do Windows"
                result.issues_list.append("Corrupção detectada nos arquivos do Windows (SFC necessita reparo)")
            else:
                result.sfc_details = f"Resultado do SFC não determinado ({res.error or 'saída não reconhecida'})"
        elif run_sfc_scan:
            result.sfc_details = "Não verificado (requer Administrador)"
        else:
            result.sfc_details = "Não verificado (verificação profunda desativada)"

        self._log(f"[OK] SO e Serviços: {len(result.stopped_services)} serviço(s) essencial(is) com problema | "
                  f"Imagem: {result.image_health or 'N/D'}")

    # ------------------------------------------------------------------ Execução

    def run_full_diagnosis(self, run_sfc: bool = False, elevated: bool = False) -> DiagnosticResult:
        """Executa a Fase 1 completa com todas as verificações do sistema."""
        result = DiagnosticResult(analyzed_at=datetime.datetime.now(), elevated=elevated)
        steps = [
            ("CPU e Memória", lambda: self.check_cpu_and_memory(result)),
            ("Armazenamento", lambda: self.check_storage(result)),
            ("Rede", lambda: self.check_network(result)),
            ("Sistema e Serviços", lambda: self.check_os_integrity_and_services(result, run_sfc_scan=run_sfc)),
        ]
        self._log("=== INICIANDO FASE 1: ANÁLISE COMPLETA DO SISTEMA ===")
        with com_initialized():
            try:
                for i, (label, step) in enumerate(steps):
                    self.progress_callback(i, len(steps), label)
                    step()
            finally:
                self._wmi_cache.clear()  # objetos COM devem ser liberados antes do CoUninitialize
        self.progress_callback(len(steps), len(steps), "Concluído")
        result.total_issues_found = len(result.issues_list)
        self._log(f"=== FASE 1 CONCLUÍDA: {result.total_issues_found} PROBLEMA(S) DETECTADO(S) ===")
        return result
