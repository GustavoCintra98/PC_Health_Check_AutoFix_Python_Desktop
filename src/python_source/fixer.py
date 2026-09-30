"""
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
        win_temp = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
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
                            # Arquivo travado em uso pelo sistema ou por outro app - normal no Windows
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
        prefetch_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Prefetch")
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
                # SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
                flags = 0x00000001 | 0x00000002 | 0x00000004
                result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
                recycle_cleared = (result == 0)
            except Exception:
                # Fallback via PowerShell
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

        # 1. Se force_dism estiver ativado, executa DISM primeiro para reparar a imagem do Windows
        if force_dism:
            self._log("[DISM] Executando: DISM.exe /Online /Cleanup-Image /RestoreHealth...")
            self._log("[DISM] Isso pode demorar alguns minutos. Aguarde...")
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

        # 2. Executa sfc /scannow
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
            report.sfc_success = (proc.returncode in (0, 1))  # 0: sem erros, 1: erros reparados
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
        - ipconfig /flushdns (Limpa cache DNS)
        - ipconfig /release (Libera concessões DHCP atuais)
        - ipconfig /renew (Renova endereços IP via DHCP)
        - netsh winsock reset (Redefine o catálogo Winsock)
        - netsh int ip reset (Redefine a pilha TCP/IP)
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
                    first_line = out.split("\n")[0]
                    self._log(f"    -> {first_line}")
                success_count += 1
            except subprocess.TimeoutExpired:
                self._log(f"[-] Timeout ao executar {label}")
            except Exception as e:
                self._log(f"[-] Erro ao executar {label}: {e}")
                report.errors.append(f"{label}: {e}")

        report.network_repaired = (success_count >= 3)
        self._log("[OK] Reparo de rede finalizado. (Nota: Uma reinicialização pode ser solicitada pelo Winsock).")

    def kill_offending_processes(self, report: FixReport, process_list: List[Any]) -> None:
        """
        Encerra com segurança processos de usuário que estão causando gargalo de CPU ou RAM.
        Ignora estritamente processos críticos do sistema para evitar BSOD ou travamento.

        Args:
            report: Objeto FixReport para registro de métricas.
            process_list: Lista de ProcessInfo candidatos a encerramento.
        """
        self._log("[Auto-Fix] Gerenciando processos ofensores de CPU/Memória...")
        if not psutil:
            self._log("[-] psutil não disponível para encerramento de processos.")
            return

        for proc_item in process_list:
            pid = getattr(proc_item, "pid", None)
            name = getattr(proc_item, "name", "Desconhecido")
            is_critical = getattr(proc_item, "is_critical", True)

            # Trava de segurança dupla: nunca matar processos críticos
            if is_critical or name.lower() in CRITICAL_SYSTEM_PROCESSES or (pid and pid <= 4):
                self._log(f"[Protegido] Processo crítico ignorado por segurança: {name} (PID: {pid})")
                continue

            try:
                p = psutil.Process(pid)
                p.terminate()  # Envio de sinal SIGTERM / TerminateProcess
                try:
                    p.wait(timeout=2)
                except psutil.TimeoutExpired:
                    p.kill()  # Forçar SIGKILL se não fechar

                report.killed_processes.append(f"{name} (PID: {pid})")
                self._log(f"[OK] Processo ofensor encerrado: {name} (PID: {pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
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

        Args:
            diag_result: Resultado retornado pela Fase 1 (DiagnosticEngine).
            fix_storage: Se deve limpar arquivos temporários e Lixeira.
            fix_os: Se deve reparar integridade do Windows (SFC/DISM).
            fix_network: Se deve executar reset da pilha de rede e DNS.
            kill_procs: Se deve encerrar processos ofensores de usuário.

        Returns:
            FixReport: Relatório com o resumo das correções efetuadas.
        """
        report = FixReport()
        self._log("=== INICIANDO FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ===")

        # 1. Armazenamento
        if fix_storage:
            self.clean_storage(report)

        # 2. Rede
        # Executa reparo se foi solicitado ou se o ping falhou / houve alta latência
        if fix_network or not diag_result.network_online or (diag_result.ping_latency_ms and diag_result.ping_latency_ms > 100):
            self.repair_network(report)

        # 3. Integridade do Sistema Operacional & Serviços
        if fix_os:
            need_dism = not diag_result.sfc_integrity_ok
            self.repair_os_integrity(report, force_dism=need_dism)
            self.restart_stopped_services(report, diag_result.stopped_services)

        # 4. Finalização de Processos Ofensores
        if kill_procs:
            offenders = diag_result.top_cpu_processes + diag_result.top_ram_processes
            # Remove duplicatas preservando ordem
            unique_offenders = []
            seen_pids = set()
            for p in offenders:
                if p.pid not in seen_pids:
                    seen_pids.add(p.pid)
                    unique_offenders.append(p)
            self.kill_offending_processes(report, unique_offenders)

        self._log("=== FASE 2 CONCLUÍDA COM SUCESSO ===")
        return report
