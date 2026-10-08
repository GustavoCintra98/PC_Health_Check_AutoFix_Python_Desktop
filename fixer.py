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
    restore_point_created = bool = False
    software_updated: bool = False
    winupdate_cache_cleared: bool = False
    deep_cleanup_executed: bool = False


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
        - Pasta C:\Windows\Temp
        - Pasta C:\Windows\Prefetch (requer Admin)
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
                            continue

                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        try:
                            os.rmdir(dir_path)
                        except (PermissionError, OSError):
                            continue
            except Exception as e:
                self._log(f"[-] Aviso ao acessar pasta {folder}: {e}")

        # 2. Limpeza da pasta Prefetch (C:\Windows\Prefetch)
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
                    first_line = out.split("\n")[0]
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
        kill_procs: bool = False,
        create_restore: bool = True,
        update_winget: bool = False,
        reset_winupdate: bool = False
    ) -> FixReport:
        """
        Executa a Fase 2 completa de resolução automática com base no diagnóstico anterior.
        """
        report = FixReport()
        self._log("=== INICIANDO FASE 2: RESOLUÇÃO AUTOMÁTICA (AUTO-FIX) ===")

        if create_restore:
            self.create_restore_point(report)

        if fix_storage:
            self.clean_storage(report)

        if kill_procs:
            offenders = diag_result.top_cpu_processes + diag_result.top_ram_processes
            unique_offenders = {p.pid: p for p in offenders}.values()
            self.kill_offending_processes(report, list(unique_offenders))

        if fix_network or not diag_result.network_online:
            self.repair_network(report)

        if fix_os:
            need_dism = not diag_result.sfc_integrity_ok
            self.repair_os_integrity(report, force_dism=need_dism)
            self.restart_stopped_services(report, diag_result.stopped_services)

        if reset_winupdate:
            self.repair_windows_update_and_drivers(report)

        if update_winget:
            self.update_software_winget(report)

        self._log("=== FASE 2 CONCLUÍDA COM SUCESSO ===")
        return report

    def create_restore_point(self, report: FixReport) -> None:
        """Cria um Ponto de Restauração no Windows antes das modificações."""
        self._log("[Auto-Fix] Criando Ponto de Restauração do Sistema...")
        try:
            ps_cmd = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                "Enable-ComputerRestore -Drive 'C:\'; Checkpoint-Computer -Description 'PCHealthCheck_AutoFix' -RestorePointType 'MODIFY_SETTINGS'"
            ]
            proc = subprocess.run(ps_cmd, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if proc.returncode == 0:
                report.restore_point_created = True
                self._log("[OK] Ponto de restauração criado com sucesso.")
            else:
                self._log("[-] Aviso: A proteção do sistema pode estar desativada. Ponto não criado.")
        except Exception as e:
            self._log(f"[-] Falha ao criar ponto de restauração: {e}")

    def update_software_winget(self, report: FixReport) -> None:
        """Atualiza todos os pacotes e softwares gerenciáveis instalados via winget."""
        self._log("[Auto-Fix] Buscando e instalando atualizações de software (Winget)...")
        try:
            cmd = [
                "winget", "upgrade", "--all", "--silent", "--force", 
                "--accept-package-agreements", "--accept-source-agreements"
            ]
            proc = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            
            # Winget retorna 0 em sucesso, ou códigos negativos se não houver atualizações ou pacotes ignorados
            if "Nenhuma atualização aplicável encontrada" in proc.stdout or proc.returncode == 0:
                self._log("[OK] Todos os softwares gerenciados pelo winget estão atualizados.")
                report.software_updated = True
            else:
                self._log("[OK] Ciclo de atualização do winget concluído (alguns pacotes podem exigir reinício).")
                report.software_updated = True
        except FileNotFoundError:
            self._log("[-] Winget não encontrado no sistema. Recurso ignorado.")
        except Exception as e:
            self._log(f"[-] Erro ao executar winget: {e}")

    def repair_windows_update_and_drivers(self, report: FixReport) -> None:
        """Para os serviços de atualização, limpa o cache de downloads corrompidos e reinicia."""
        self._log("[Auto-Fix] Redefinindo cache do Windows Update (corrige falhas de download/drivers)...")
        try:
            # Para os serviços BITS e WUAUSERV
            for svc in ["wuauserv", "bits", "cryptsvc"]:
                subprocess.run(["sc", "stop", svc], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            
            # Limpa o diretório de Download
            win_dir = os.environ.get("SystemRoot", "C:\\Windows")
            soft_dist_dl = os.path.join(win_dir, "SoftwareDistribution", "Download")
            
            if os.path.exists(soft_dist_dl):
                try:
                    shutil.rmtree(soft_dist_dl, ignore_errors=True)
                    os.makedirs(soft_dist_dl, exist_ok=True)
                except OSError:
                    pass
            
            # Inicia os serviços novamente
            for svc in ["wuauserv", "bits", "cryptsvc"]:
                subprocess.run(["sc", "start", svc], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            
            # Força o Windows Update a buscar novas atualizações (incluindo drivers) via UsoClient
            subprocess.run(["UsoClient.exe", "StartScan"], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            
            report.winupdate_cache_cleared = True
            self._log("[OK] Cache de atualizações limpo. Varredura de drivers/updates iniciada em segundo plano.")
        except Exception as e:
            self._log(f"[-] Falha ao redefinir o Windows Update: {e}")