r"""
PC Health Check & Auto-Fix - Resolution Engine (Fase 2).

Este módulo executa a resolução automática de problemas do sistema Windows:
1. Ponto de Restauração antes de qualquer modificação (com confirmação se falhar).
2. Armazenamento: limpeza de %TEMP% e C:\Windows\Temp (arquivos com mais de 24h,
   sem atravessar junctions) e, opcionalmente, esvaziamento da Lixeira.
3. Rede: reparo escalonado — flush DNS; renovação DHCP apenas se houver falha;
   reset de Winsock/TCP-IP apenas se a conectividade não voltar.
4. SO: DISM /RestoreHealth (se a imagem não estiver saudável) + sfc /scannow,
   e reinício de serviços essenciais com verificação real do estado.
5. Processos: encerra apenas processos que comprovadamente causam gargalo,
   validando que o PID não foi reutilizado.
6. Windows Update (reset de cache) e atualização de apps via winget.

Cada ação registra um StepResult com o resultado verificado — nada é
reportado como sucesso sem checar o código de saída ou o estado final.
"""

import ctypes
import os
import re
import sys
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from typing import Callable, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

from diagnostics import (
    CRITICAL_SYSTEM_PROCESSES, TEMP_MIN_AGE_HOURS, DiagnosticResult, ProcessInfo,
    check_dns, check_internet_tcp, own_process_tree_pids, parse_sfc_output,
)
from utils import (
    SFC_ENCODING, delete_file, get_protected_paths, get_temp_dirs, iter_old_files,
    remove_empty_dirs, run_cmd, run_powershell, stream_cmd,
)

# Códigos de retorno conhecidos
REBOOT_REQUIRED_CODE = 3010
WINGET_NO_APPLICABLE_UPDATE = 0x8A15002B
E_UNEXPECTED = -2147418113  # SHEmptyRecycleBinW quando a Lixeira já está vazia

WINUPDATE_SERVICES = ["wuauserv", "bits", "cryptsvc"]


@dataclass
class FixOptions:
    """Ações selecionadas pelo usuário para a Fase 2."""
    create_restore: bool = True
    clean_temp: bool = True
    empty_recycle_bin: bool = False
    fix_network: bool = True
    fix_os: bool = True
    kill_procs: bool = False
    update_winget: bool = False
    reset_winupdate: bool = False


# Opções que exigem privilégios de Administrador
ADMIN_ONLY_OPTIONS = {"create_restore", "fix_network", "fix_os", "reset_winupdate"}


@dataclass
class StepResult:
    """Resultado verificado de uma etapa do Auto-Fix."""
    name: str
    status: str          # "ok", "warning", "error" ou "skipped"
    detail: str = ""


@dataclass
class FixReport:
    """Relatório estruturado das ações de correção executadas."""
    steps: List[StepResult] = field(default_factory=list)
    temp_files_deleted: int = 0
    temp_files_skipped: int = 0
    temp_space_freed_mb: float = 0.0
    recycle_bin_cleared: bool = False
    restore_point_created: bool = False
    network_repaired: bool = False
    sfc_executed: bool = False
    sfc_result: Optional[str] = None
    dism_executed: bool = False
    dism_success: bool = False
    services_restarted: List[str] = field(default_factory=list)
    killed_processes: List[str] = field(default_factory=list)
    software_updated: bool = False
    winupdate_cache_cleared: bool = False
    reboot_required: bool = False
    cancelled: bool = False
    aborted_reason: Optional[str] = None

    def add(self, name: str, status: str, detail: str = "") -> StepResult:
        step = StepResult(name, status, detail)
        self.steps.append(step)
        return step

    @property
    def errors(self) -> List[str]:
        return [f"{s.name}: {s.detail}" for s in self.steps if s.status == "error"]


def describe_plan(options: FixOptions, diag: DiagnosticResult) -> List[str]:
    """Descreve, em linguagem simples, o que será feito e os impactos — usado na confirmação."""
    lines: List[str] = []
    if options.create_restore:
        lines.append("• Criar ponto de restauração (o Windows permite apenas 1 a cada 24h).")
    if options.clean_temp:
        lines.append(f"• Apagar arquivos temporários com mais de {TEMP_MIN_AGE_HOURS:.0f}h "
                     f"(~{diag.temp_files_size_mb:.0f} MB).")
    if options.empty_recycle_bin:
        lines.append("• ESVAZIAR A LIXEIRA — os arquivos não poderão ser recuperados.")
    if options.fix_network:
        if diag.network_online and diag.dns_ok is not False:
            lines.append("• Rede: limpar cache DNS (a conexão está funcionando, nada além disso).")
        else:
            lines.append("• Rede: reparo escalonado (DNS → renovar IP → reset Winsock/TCP-IP). "
                         "A conexão pode cair por alguns segundos e o reset exige reiniciar.")
    if options.fix_os:
        dism = "DISM /RestoreHealth + " if diag.image_health != "Healthy" else ""
        lines.append(f"• Reparar o Windows: {dism}sfc /scannow (pode levar de 15 a 40 minutos).")
        startable = [s["display"] for s in diag.stopped_services if s.get("start_type") != "disabled"]
        if startable:
            lines.append(f"• Iniciar serviços parados: {', '.join(startable)}.")
    if options.kill_procs:
        if diag.offending_processes:
            names = ", ".join(f"{p.name} (PID {p.pid})" for p in diag.offending_processes)
            lines.append(f"• ENCERRAR processos que causam gargalo: {names}. Dados não salvos serão perdidos.")
        else:
            lines.append("• Encerrar processos: nenhum processo está causando gargalo — nada será encerrado.")
    if options.reset_winupdate:
        lines.append("• Parar o Windows Update e limpar o cache de downloads.")
    if options.update_winget:
        lines.append("• Atualizar todos os aplicativos via winget (programas abertos podem ser fechados).")
    return lines


class _ProgressLineFilter:
    """
    Repassa linhas de saída ao log, mas reduz barras de progresso (DISM/SFC)
    a uma linha a cada 10%, evitando milhares de linhas no console.
    """
    _PCT_RE = re.compile(r"(\d{1,3})(?:[.,]\d+)?\s*%")

    def __init__(self, prefix: str, log: Callable[[str], None]):
        self.prefix = prefix
        self.log = log
        self.last_bucket = -1

    def __call__(self, line: str) -> None:
        match = self._PCT_RE.search(line)
        if match:
            bucket = int(match.group(1)) // 10
            if bucket == self.last_bucket:
                return
            self.last_bucket = bucket
            line = f"Progresso: {int(match.group(1))}%"
        self.log(f"[{self.prefix}] {line}")


class _DeletionProgress:
    """
    Registra o andamento de exclusões longas (ex.: 300 mil arquivos no cache do
    Windows Update levam minutos) a cada `interval` segundos, para o app não
    parecer travado. Limitar por tempo, e não por quantidade, mantém o log
    enxuto tanto em discos rápidos quanto lentos.
    """

    def __init__(self, label: str, log: Callable[[str], None], interval: float = 3.0):
        self.label = label
        self.log = log
        self.interval = interval
        self.deleted = 0
        self.freed = 0
        self.next_report = time.monotonic() + interval

    def add(self, size: int) -> None:
        self.deleted += 1
        self.freed += size
        now = time.monotonic()
        if now >= self.next_report:
            self.next_report = now + self.interval
            self.log(f"[{self.label}] {self.deleted} arquivos removidos ({self.freed / (1024 * 1024):.0f} MB) até agora...")


def _winget_line_filter(log: Callable[[str], None]) -> Callable[[str], None]:
    """Remove spinners e barras de download do winget."""
    def _filter(line: str) -> None:
        if len(line) <= 2 or any(ch in line for ch in "█▒") or re.fullmatch(r"[-\\|/ ]+", line):
            return
        log(f"[Winget] {line}")
    return _filter


def _service_status(name: str) -> str:
    if not psutil:
        return "unknown"
    try:
        return psutil.win_service_get(name).status()
    except Exception:
        return "unknown"


def _wait_service_status(name: str, wanted: str, timeout: float = 30) -> bool:
    """Aguarda o serviço atingir o estado desejado (sc start/stop retornam antes de concluir)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _service_status(name) == wanted:
            return True
        time.sleep(1)
    return _service_status(name) == wanted


class AutoFixEngine:
    """Motor de resolução automática e otimização para Windows."""

    def __init__(
        self,
        log_callback: Optional[Callable[[str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        confirm_callback: Optional[Callable[[str, str], bool]] = None,
    ):
        """
        Args:
            log_callback: Recebe mensagens de log em tempo real.
            progress_callback: Recebe (etapa_atual, total_etapas, descrição).
            confirm_callback: Pergunta sim/não ao usuário (título, mensagem) e
                bloqueia até a resposta. Sem callback, a resposta é "não".
        """
        self.log_callback = log_callback or (lambda msg: None)
        self.progress_callback = progress_callback or (lambda i, n, label: None)
        self.confirm_callback = confirm_callback or (lambda title, msg: False)

    def _log(self, message: str) -> None:
        self.log_callback(message)

    # ------------------------------------------------------- Ponto de restauração

    def create_restore_point(self, report: FixReport) -> bool:
        """
        Cria um Ponto de Restauração e confirma que ele realmente existe.

        O Checkpoint-Computer retorna sucesso mesmo quando o Windows recusa criar
        o ponto (limite de 1 a cada 24h), então comparamos o número de sequência
        antes e depois.
        """
        self._log("[Auto-Fix] Criando Ponto de Restauração do Sistema...")
        script = r"""
try {
    try { Enable-ComputerRestore -Drive "$env:SystemDrive\" -ErrorAction Stop } catch {}
    $prev = (Get-ComputerRestorePoint | Measure-Object -Property SequenceNumber -Maximum).Maximum
    Checkpoint-Computer -Description 'PCHealthCheck AutoFix' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop -WarningAction SilentlyContinue
    $last = Get-ComputerRestorePoint | Sort-Object SequenceNumber | Select-Object -Last 1
    if (-not $last) { 'NONE' }
    elseif ($last.SequenceNumber -gt $prev) { 'CREATED' }
    else {
        $age = (Get-Date) - $last.ConvertToDateTime($last.CreationTime)
        if ($age.TotalHours -lt 24) { 'RECENT|' + [int]$age.TotalHours } else { 'NONE' }
    }
} catch { 'ERROR|' + $_.Exception.Message }
"""
        res = run_powershell(script, timeout=300)
        last_line = res.output.strip().splitlines()[-1] if res.output.strip() else ""

        if last_line == "CREATED":
            report.restore_point_created = True
            report.add("Ponto de restauração", "ok", "Criado com sucesso")
            self._log("[OK] Ponto de restauração criado com sucesso.")
            return True
        if last_line.startswith("RECENT|"):
            hours = last_line.split("|", 1)[1]
            report.restore_point_created = True
            report.add("Ponto de restauração", "ok", f"Já existe um ponto criado há {hours}h (limite do Windows: 1 a cada 24h)")
            self._log(f"[OK] O Windows não cria outro ponto em menos de 24h; será usado o ponto existente (criado há {hours}h).")
            return True

        reason = (last_line.split("|", 1)[1] if last_line.startswith("ERROR|")
                  else res.error or "a Proteção do Sistema pode estar desativada")
        report.add("Ponto de restauração", "error", reason)
        self._log(f"[-] Ponto de restauração NÃO foi criado: {reason}")
        return False

    # ------------------------------------------------------------- Armazenamento

    def clean_storage(self, report: FixReport) -> None:
        r"""
        Remove arquivos com mais de 24h de %TEMP% e C:\Windows\Temp.

        - Não segue junctions/symlinks (evita apagar arquivos fora do TEMP).
        - Ignora a pasta de extração do próprio .exe (PyInstaller _MEIxxxx).
        - Arquivos em uso são contabilizados como ignorados, sem travar o app.
        """
        self._log("[Auto-Fix] Iniciando limpeza de arquivos temporários...")
        protected = get_protected_paths()
        progress = _DeletionProgress("Limpeza", self._log)
        skipped = 0
        for folder in get_temp_dirs():
            self._log(f"[*] Limpando diretório: {folder}")
            for path, size in iter_old_files(folder, TEMP_MIN_AGE_HOURS, protected):
                if delete_file(path):
                    progress.add(size)
                else:
                    skipped += 1
            remove_empty_dirs(folder, TEMP_MIN_AGE_HOURS, protected)

        report.temp_files_deleted = progress.deleted
        report.temp_files_skipped = skipped
        report.temp_space_freed_mb = round(progress.freed / (1024 * 1024), 2)
        detail = f"{progress.deleted} arquivos removidos ({report.temp_space_freed_mb} MB); {skipped} em uso ignorados"
        report.add("Limpeza de temporários", "ok", detail)
        self._log(f"[OK] Limpeza concluída: {detail}.")

    def empty_recycle_bin(self, report: FixReport) -> None:
        self._log("[Auto-Fix] Esvaziando a Lixeira do Windows...")
        if sys.platform != "win32":
            report.add("Lixeira", "skipped", "Disponível apenas no Windows")
            return
        flags = 0x1 | 0x2 | 0x4  # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        fn = ctypes.windll.shell32.SHEmptyRecycleBinW
        fn.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD]
        fn.restype = ctypes.c_long  # HRESULT
        hr = fn(None, None, flags)
        if hr == 0:
            report.recycle_bin_cleared = True
            report.add("Lixeira", "ok", "Esvaziada")
            self._log("[OK] Lixeira esvaziada.")
        elif hr == E_UNEXPECTED:
            report.recycle_bin_cleared = True
            report.add("Lixeira", "ok", "Já estava vazia")
            self._log("[OK] A Lixeira já estava vazia.")
        else:
            report.add("Lixeira", "error", f"HRESULT 0x{hr & 0xFFFFFFFF:08X}")
            self._log(f"[-] Falha ao esvaziar a Lixeira (HRESULT 0x{hr & 0xFFFFFFFF:08X}).")

    # ------------------------------------------------------------- SO / Serviços

    def repair_os_integrity(self, report: FixReport, diag: DiagnosticResult) -> None:
        """
        1. DISM /RestoreHealth — somente se a imagem não foi confirmada como saudável.
        2. sfc /scannow — substitui arquivos corrompidos pelas cópias do repositório.
        """
        self._log("[Auto-Fix] Iniciando reparo de integridade do Sistema Operacional...")

        if diag.image_health == "Healthy":
            self._log("[DISM] Imagem do Windows saudável — RestoreHealth dispensado.")
        else:
            self._log("[DISM] Executando DISM /Online /Cleanup-Image /RestoreHealth...")
            res = stream_cmd(
                ["dism.exe", "/Online", "/Cleanup-Image", "/RestoreHealth"],
                on_line=_ProgressLineFilter("DISM", self._log),
                timeout=3600,
            )
            report.dism_executed = True
            report.dism_success = res.returncode in (0, REBOOT_REQUIRED_CODE)
            if res.returncode == REBOOT_REQUIRED_CODE:
                report.reboot_required = True
            if report.dism_success:
                report.add("DISM RestoreHealth", "ok", "Imagem reparada/verificada")
                self._log("[OK] DISM concluído com sucesso.")
            else:
                detail = res.error or f"código de saída {res.returncode}"
                report.add("DISM RestoreHealth", "error", detail)
                self._log(f"[-] DISM falhou ({detail}). Consulte C:\\Windows\\Logs\\DISM\\dism.log")

        self._log("[SFC] Executando sfc /scannow (pode levar vários minutos)...")
        res = stream_cmd(
            ["sfc", "/scannow"],
            on_line=_ProgressLineFilter("SFC", self._log),
            timeout=3600,
            encoding=SFC_ENCODING,
        )
        report.sfc_executed = True
        report.sfc_result = parse_sfc_output(res.output)
        cbs = r"C:\Windows\Logs\CBS\CBS.log"
        if report.sfc_result == "ok":
            report.add("SFC /scannow", "ok", "Nenhuma violação de integridade")
        elif report.sfc_result == "repaired":
            report.reboot_required = True
            report.add("SFC /scannow", "ok", "Arquivos corrompidos reparados (reinicie o PC)")
        elif report.sfc_result == "unrepairable":
            report.add("SFC /scannow", "error", f"Há arquivos que não puderam ser reparados — veja {cbs}")
        else:
            report.add("SFC /scannow", "warning", res.error or f"resultado não reconhecido (código {res.returncode})")
        self._log(f"[OK] SFC finalizado: {report.steps[-1].detail}")

    def restart_stopped_services(self, report: FixReport, stopped_services: List[dict]) -> None:
        """Inicia serviços essenciais parados e confirma que entraram em execução."""
        if not stopped_services:
            return
        self._log("[Auto-Fix] Iniciando serviços essenciais parados...")
        for srv in stopped_services:
            name = srv.get("name")
            display = srv.get("display", name)
            if srv.get("start_type") == "disabled":
                report.add(f"Serviço {display}", "warning",
                           "Desativado — não foi alterado (pode ter sido desativado por política). Reative em services.msc se necessário.")
                self._log(f"[!] {display} está DESATIVADO; não será alterado automaticamente.")
                continue
            self._log(f"[*] Iniciando serviço: {display} ({name})...")
            res = run_cmd(["sc", "start", name], timeout=30)
            if _wait_service_status(name, "running", timeout=30):
                report.services_restarted.append(display)
                report.add(f"Serviço {display}", "ok", "Em execução")
                self._log(f"[OK] {display} em execução.")
            else:
                detail = res.error or f"não iniciou (sc código {res.returncode})"
                report.add(f"Serviço {display}", "error", detail)
                self._log(f"[-] {display} {detail}.")

    # -------------------------------------------------------------------- Rede

    def repair_network(self, report: FixReport, diag: DiagnosticResult) -> None:
        """
        Reparo escalonado — só avança de nível se o problema persistir:
        1. ipconfig /flushdns (sempre, inofensivo)
        2. ipconfig /release + /renew (somente sem Internet ou com DNS falhando)
        3. netsh winsock reset + netsh int ip reset (somente se ainda sem conexão; exige reiniciar)
        """
        self._log("[Auto-Fix] Reparo de rede...")
        res = run_cmd(["ipconfig", "/flushdns"], timeout=30)
        self._log(f"[*] Cache DNS limpo ({'OK' if res.ok else res.error or f'código {res.returncode}'}).")

        if diag.network_online and diag.dns_ok is not False:
            detail = "Conexão funcionando: apenas o cache DNS foi limpo"
            if not diag.network_healthy:
                detail += ". Latência alta/perda de pacotes costuma ser física (Wi-Fi, cabo, provedor) — não se resolve com reset de software"
            report.network_repaired = res.ok
            report.add("Rede", "ok" if res.ok else "warning", detail)
            self._log(f"[OK] {detail}.")
            return

        if check_internet_tcp() is not None and check_dns():
            report.network_repaired = True
            report.add("Rede", "ok", "Conectividade restaurada após limpar o cache DNS")
            self._log("[OK] Conectividade restaurada após limpar o cache DNS.")
            return

        self._log("[*] Renovando concessão de IP (DHCP)...")
        run_cmd(["ipconfig", "/release"], timeout=30)
        renew = run_cmd(["ipconfig", "/renew"], timeout=90)
        time.sleep(3)
        if check_internet_tcp() is not None and check_dns():
            report.network_repaired = True
            report.add("Rede", "ok", "Conectividade restaurada após renovar o IP")
            self._log("[OK] Conectividade restaurada após renovar o IP.")
            return
        if not renew.ok:
            self._log(f"[-] ipconfig /renew: {renew.error or f'código {renew.returncode}'}")

        self._log("[*] Redefinindo Winsock e pilha TCP/IP...")
        failures = []
        for args in (["netsh", "winsock", "reset"], ["netsh", "int", "ip", "reset"]):
            r = run_cmd(args, timeout=60)
            if not r.ok:
                failures.append(f"{' '.join(args)}: {r.error or f'código {r.returncode}'}")
        if failures:
            report.add("Rede", "error", "; ".join(failures))
            self._log(f"[-] Falha no reset de rede: {'; '.join(failures)}")
        else:
            report.network_repaired = True
            report.reboot_required = True
            report.add("Rede", "warning", "Winsock e TCP/IP redefinidos — REINICIE o PC para concluir")
            self._log("[OK] Winsock e TCP/IP redefinidos. É necessário reiniciar o computador.")

    # --------------------------------------------------------------- Processos

    def kill_offending_processes(self, report: FixReport, process_list: List[ProcessInfo]) -> None:
        """
        Encerra apenas os processos identificados como causadores de gargalo.
        Antes de encerrar, confirma que o PID ainda pertence ao mesmo processo
        (nome + horário de criação), evitando matar um processo que reutilizou o PID.
        """
        self._log("[Auto-Fix] Gerenciando processos ofensores de CPU/Memória...")
        if not psutil:
            report.add("Processos", "skipped", "psutil indisponível")
            return
        if not process_list:
            report.add("Processos", "skipped", "Nenhum processo causando gargalo")
            self._log("[*] Nenhum processo está causando gargalo — nada a encerrar.")
            return

        own = own_process_tree_pids()
        for info in process_list:
            label = f"{info.name} (PID: {info.pid})"
            if info.is_critical or info.name.lower() in CRITICAL_SYSTEM_PROCESSES or info.pid <= 4 or info.pid in own:
                self._log(f"[Protegido] Processo ignorado por segurança: {label}")
                continue
            try:
                p = psutil.Process(info.pid)
                if p.name() != info.name or abs(p.create_time() - info.create_time) > 1:
                    self._log(f"[*] {label} já foi encerrado (o PID agora pertence a outro processo).")
                    continue
                p.terminate()
                try:
                    p.wait(timeout=5)
                except psutil.TimeoutExpired:
                    p.kill()
                report.killed_processes.append(label)
                report.add(f"Encerrar {info.name}", "ok", f"PID {info.pid}")
                self._log(f"[OK] Processo encerrado: {label}")
            except psutil.NoSuchProcess:
                self._log(f"[*] {label} já havia sido encerrado.")
            except psutil.Error as e:
                report.add(f"Encerrar {info.name}", "error", str(e))
                self._log(f"[-] Não foi possível encerrar {label}: {e}")

    # ----------------------------------------------------------- Windows Update

    def repair_windows_update(self, report: FixReport) -> None:
        """Para os serviços do Windows Update, limpa o cache de downloads e restaura os serviços."""
        self._log("[Auto-Fix] Redefinindo cache do Windows Update...")
        was_running = {svc: _service_status(svc) == "running" for svc in WINUPDATE_SERVICES}

        not_stopped = []
        for svc in WINUPDATE_SERVICES:
            run_cmd(["sc", "stop", svc], timeout=30)
            if not _wait_service_status(svc, "stopped", timeout=45):
                not_stopped.append(svc)

        if not_stopped:
            detail = f"Serviços não pararam: {', '.join(not_stopped)} — cache não foi limpo"
            report.add("Windows Update", "error", detail)
            self._log(f"[-] {detail}.")
        else:
            win_dir = os.environ.get("SystemRoot", r"C:\Windows")
            download_dir = os.path.join(win_dir, "SoftwareDistribution", "Download")
            progress = _DeletionProgress("Windows Update", self._log)
            skipped = 0
            if os.path.isdir(download_dir):
                self._log(f"[*] Limpando diretório: {download_dir}")
                for path, size in iter_old_files(download_dir, 0):
                    if delete_file(path):
                        progress.add(size)
                    else:
                        skipped += 1
                remove_empty_dirs(download_dir)
            report.winupdate_cache_cleared = skipped == 0
            status = "ok" if skipped == 0 else "warning"
            detail = (f"{progress.deleted} arquivos de cache removidos ({progress.freed / (1024 * 1024):.0f} MB)"
                      + (f"; {skipped} bloqueados" if skipped else ""))
            report.add("Windows Update", status, detail + ". Abra Configurações > Windows Update e clique em 'Verificar atualizações'.")
            self._log(f"[OK] Cache do Windows Update limpo: {detail}.")

        # cryptsvc é automático e sempre deve voltar; os demais voltam se estavam rodando
        for svc in WINUPDATE_SERVICES:
            if svc == "cryptsvc" or was_running[svc]:
                run_cmd(["sc", "start", svc], timeout=30)
                if not _wait_service_status(svc, "running", timeout=30):
                    report.add(f"Serviço {svc}", "error", "Não voltou a executar após o reset")
                    self._log(f"[-] O serviço {svc} não voltou a executar.")

    # ------------------------------------------------------------------ Winget

    def update_software_winget(self, report: FixReport) -> None:
        """Atualiza aplicativos via winget com saída em tempo real e timeout."""
        self._log("[Auto-Fix] Buscando e instalando atualizações de software (Winget)...")
        res = stream_cmd(
            ["winget", "upgrade", "--all", "--silent",
             "--accept-package-agreements", "--accept-source-agreements"],
            on_line=_winget_line_filter(self._log),
            timeout=3600,
            encoding="utf-8",
        )
        if res.returncode is None:
            if res.timed_out:
                report.add("Winget", "error", res.error)
                self._log(f"[-] Winget interrompido: {res.error}.")
            else:
                report.add("Winget", "skipped", "winget não encontrado (instale o 'Instalador de Aplicativo' pela Microsoft Store)")
                self._log("[-] Winget não encontrado no sistema. Recurso ignorado.")
            return

        code = res.returncode & 0xFFFFFFFF
        if code in (0, WINGET_NO_APPLICABLE_UPDATE):
            report.software_updated = True
            report.add("Winget", "ok", "Aplicativos atualizados" if code == 0 else "Nenhuma atualização disponível")
            self._log("[OK] Atualização via winget concluída.")
        else:
            report.add("Winget", "warning", f"Alguns pacotes falharam (código 0x{code:08X}); veja o log")
            self._log(f"[!] Winget terminou com código 0x{code:08X}: alguns pacotes podem não ter sido atualizados.")

    # ---------------------------------------------------------------- Execução

    def run_auto_fix(
        self,
        diag_result: DiagnosticResult,
        options: FixOptions,
        cancel_event: Optional[threading.Event] = None,
    ) -> FixReport:
        """
        Executa a Fase 2 com base no diagnóstico anterior.

        O cancelamento é verificado entre as etapas (interromper SFC/DISM/instaladores
        no meio poderia deixar o sistema em estado inconsistente).
        """
        report = FixReport()
        cancel_event = cancel_event or threading.Event()
        self._log("=== INICIANDO FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ===")

        steps = []
        if options.clean_temp:
            steps.append(("clean_temp", "Limpando temporários", lambda: self.clean_storage(report)))
        if options.empty_recycle_bin:
            steps.append(("empty_recycle_bin", "Esvaziando a Lixeira", lambda: self.empty_recycle_bin(report)))
        if options.kill_procs:
            steps.append(("kill_procs", "Encerrando processos ofensores",
                          lambda: self.kill_offending_processes(report, diag_result.offending_processes)))
        if options.fix_network:
            steps.append(("fix_network", "Reparando rede", lambda: self.repair_network(report, diag_result)))
        if options.fix_os:
            steps.append(("fix_os", "Reparando o Windows (DISM/SFC)", lambda: self.repair_os_integrity(report, diag_result)))
            steps.append(("fix_os", "Iniciando serviços",
                          lambda: self.restart_stopped_services(report, diag_result.stopped_services)))
        if options.reset_winupdate:
            steps.append(("reset_winupdate", "Redefinindo Windows Update", lambda: self.repair_windows_update(report)))
        if options.update_winget:
            steps.append(("update_winget", "Atualizando aplicativos (winget)", lambda: self.update_software_winget(report)))

        total = len(steps) + (1 if options.create_restore else 0)
        index = 0

        if options.create_restore:
            self.progress_callback(index, total, "Criando ponto de restauração")
            index += 1
            if not diag_result.elevated:
                report.add("Ponto de restauração", "skipped", "Requer Administrador")
            elif not self.create_restore_point(report):
                proceed = self.confirm_callback(
                    "Ponto de restauração não criado",
                    "Não foi possível criar um ponto de restauração.\n\n"
                    "Deseja continuar com as correções mesmo assim?\n"
                    "(Sem ponto de restauração não será possível desfazer as alterações.)",
                )
                if not proceed:
                    report.aborted_reason = "Cancelado pelo usuário: ponto de restauração não foi criado"
                    self._log(f"[!] {report.aborted_reason}.")
                    return report

        for key, label, action in steps:
            if cancel_event.is_set():
                report.cancelled = True
                self._log("[!] Operação cancelada pelo usuário. Etapas restantes não foram executadas.")
                break
            self.progress_callback(index, total, label)
            index += 1
            if key in ADMIN_ONLY_OPTIONS and not diag_result.elevated:
                report.add(label, "skipped", "Requer Administrador")
                self._log(f"[*] {label}: ignorado (requer Administrador).")
                continue
            try:
                action()
            except Exception as e:  # uma etapa com erro não deve impedir as demais
                report.add(label, "error", f"Erro inesperado: {e}")
                self._log(f"[-] Erro inesperado em '{label}': {e}")

        self.progress_callback(total, total, "Concluído")
        errors = len(report.errors)
        status = "CANCELADA" if report.cancelled else ("CONCLUÍDA COM ERROS" if errors else "CONCLUÍDA")
        self._log(f"=== FASE 2 {status} ({errors} erro(s)) ===")
        if report.reboot_required:
            self._log("[!] REINICIE o computador para concluir os reparos.")
        return report
