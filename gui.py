"""
PC Health Check & Auto-Fix - Graphical User Interface (CustomTkinter).

Interface gráfica moderna para Windows utilizando CustomTkinter.
As operações rodam em threads de trabalho; toda atualização de widgets passa
por uma fila consumida na thread principal (o Tkinter não é thread-safe).
"""

import collections
import datetime
import queue
import threading
import time
import tkinter.filedialog as fd
from tkinter import messagebox
from typing import Callable, Optional

try:
    import customtkinter as ctk
except ImportError:
    ctk = None

from diagnostics import DiagnosticEngine, DiagnosticResult
from fixer import ADMIN_ONLY_OPTIONS, AutoFixEngine, FixOptions, FixReport, describe_plan
from report import build_text_report
from utils import logger

APP_VERSION = "v3.0"
MAX_LOG_LINES = 5000          # linhas mantidas no console da interface
MAX_HISTORY_LINES = 20000     # linhas mantidas em memória para o relatório
STALE_ANALYSIS_MINUTES = 30

# (atributo FixOptions, rótulo, marcado por padrão)
FIX_OPTION_WIDGETS = [
    ("create_restore", "Criar Ponto de Restauração", True),
    ("clean_temp", "Limpar Arquivos Temporários", True),
    ("empty_recycle_bin", "Esvaziar Lixeira", False),
    ("fix_network", "Reparar Rede / DNS", True),
    ("fix_os", "Reparar Windows (DISM/SFC)", True),
    ("kill_procs", "Encerrar Processos Gargalo", False),
    ("reset_winupdate", "Reparar Windows Update", False),
    ("update_winget", "Atualizar Apps (Winget)", False),
]


class PCHealthApp(ctk.CTk if ctk else object):
    """Janela principal do aplicativo desktop PC Health Check & Auto-Fix."""

    def __init__(self, is_elevated: bool = True, log_path: Optional[str] = None):
        if not ctk:
            raise ImportError("CustomTkinter não está instalado. Execute: pip install customtkinter")

        super().__init__()

        self.is_elevated = is_elevated
        self.log_path = log_path
        self.last_diagnostic: Optional[DiagnosticResult] = None
        self.last_fix_report: Optional[FixReport] = None

        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._log_history: collections.deque = collections.deque(maxlen=MAX_HISTORY_LINES)
        self._busy = False
        self._busy_since = 0.0
        self._status_text = "Pronto"
        self._cancel_event: Optional[threading.Event] = None

        self.diagnostic_engine = DiagnosticEngine(
            log_callback=self._append_log,
            progress_callback=self._report_progress,
        )
        self.fix_engine = AutoFixEngine(
            log_callback=self._append_log,
            progress_callback=self._report_progress,
            confirm_callback=self._ask_from_worker,
        )

        # Configurações de Janela
        self.title("PC Health Check & Auto-Fix - Windows System Optimizer")
        self.geometry("1100x780")
        self.minsize(980, 720)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_ui()
        self._set_busy(False)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<F1>", lambda e: self._trigger(self.btn_analyze, self.start_analysis_thread))
        self.bind("<F2>", lambda e: self._trigger(self.btn_fix, self.start_autofix_thread))
        self.after(50, self._process_ui_queue)
        self.after(1000, self._tick_elapsed)

        uac = "Elevado (Admin)" if self.is_elevated else "Não-Elevado (funções de reparo limitadas)"
        self._append_log(f"[{datetime.datetime.now():%H:%M:%S}] Sistema pronto. UAC: {uac}")
        if self.log_path:
            self._append_log(f"[*] Log em arquivo: {self.log_path}")

    # ------------------------------------------------------------------ Layout

    def _build_ui(self) -> None:
        """Monta a estrutura de widgets da interface."""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ BARRA LATERAL (SIDEBAR) ------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        row = 0
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PC Health Check\n& Auto-Fix",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=row, column=0, padx=20, pady=(20, 8))
        row += 1

        self.uac_badge = ctk.CTkLabel(
            self.sidebar_frame,
            text="Privilégio: Administrador" if self.is_elevated else "Aviso: Sem Admin (reparos limitados)",
            text_color="#10b981" if self.is_elevated else "#f59e0b",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.uac_badge.grid(row=row, column=0, padx=20, pady=(0, 14))
        row += 1

        # Fase 1: Análise
        self.btn_analyze = ctk.CTkButton(
            self.sidebar_frame,
            text="  Iniciar Análise (F1)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=self.start_analysis_thread,
        )
        self.btn_analyze.grid(row=row, column=0, padx=20, pady=(4, 2), sticky="ew")
        row += 1

        self.chk_deep_sfc = ctk.CTkCheckBox(self.sidebar_frame, text="Incluir SFC (lento, ~10 min)")
        self.chk_deep_sfc.grid(row=row, column=0, padx=20, pady=(2, 8), sticky="w")
        if not self.is_elevated:
            self.chk_deep_sfc.configure(state="disabled")
        row += 1

        # Fase 2: Auto-Fix (habilitado somente após uma análise)
        self.btn_fix = ctk.CTkButton(
            self.sidebar_frame,
            text="  Corrigir Selecionados (F2)",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_autofix_thread,
        )
        self.btn_fix.grid(row=row, column=0, padx=20, pady=4, sticky="ew")
        row += 1

        self.opt_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Opções de Reparo:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.opt_label.grid(row=row, column=0, padx=20, pady=(10, 2), sticky="w")
        row += 1

        self.fix_checkboxes = {}
        for key, label, default in FIX_OPTION_WIDGETS:
            admin_only = key in ADMIN_ONLY_OPTIONS and not self.is_elevated
            chk = ctk.CTkCheckBox(self.sidebar_frame, text=label + (" (Admin)" if admin_only else ""))
            if default and not admin_only:
                chk.select()
            chk.grid(row=row, column=0, padx=20, pady=2, sticky="w")
            self.fix_checkboxes[key] = (chk, admin_only)
            row += 1

        # Linha elástica empurra relatório e versão para o rodapé
        self.sidebar_frame.grid_rowconfigure(row, weight=1)
        row += 1

        self.btn_report = ctk.CTkButton(
            self.sidebar_frame,
            text="  Gerar Relatório",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self.export_report,
        )
        self.btn_report.grid(row=row, column=0, padx=20, pady=(12, 6), sticky="ew")
        row += 1

        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text=f"{APP_VERSION} · Windows 10/11 x64",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
        )
        self.version_label.grid(row=row, column=0, padx=20, pady=(0, 12))

        # ------------------ ÁREA DE CONTEÚDO PRINCIPAL ------------------
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(3, weight=1)

        # Status + Cancelar
        self.status_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.lbl_status = ctk.CTkLabel(self.status_frame, text="Pronto", anchor="w",
                                       font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self.btn_cancel = ctk.CTkButton(
            self.status_frame, text="Cancelar", width=100, height=28,
            fg_color="#b91c1c", hover_color="#991b1b", command=self.cancel_operation,
        )
        self.btn_cancel.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(self.main_content, height=8)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.progress_bar.set(0)

        # Painel de Cards de Diagnóstico
        self.cards_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.cards_frame.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        self.cards_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_cpu_stats = self._make_card(0, 0, "⚙️ CPU & Memória RAM")
        self.lbl_disk_stats = self._make_card(0, 1, "💾 Armazenamento & Disco")
        self.lbl_net_stats = self._make_card(1, 0, "🌐 Rede & Conectividade")
        self.lbl_os_stats = self._make_card(1, 1, "🛡️ Sistema & Serviços")

        # Console
        self.log_container = ctk.CTkFrame(self.main_content, corner_radius=8)
        self.log_container.grid(row=3, column=0, sticky="nsew")
        self.log_container.grid_rowconfigure(1, weight=1)
        self.log_container.grid_columnconfigure(0, weight=1)

        self.log_header = ctk.CTkLabel(
            self.log_container,
            text="Terminal de Execução e Logs em Tempo Real",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.log_header.grid(row=0, column=0, padx=14, pady=(8, 4), sticky="w")

        self.txt_log = ctk.CTkTextbox(
            self.log_container,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            fg_color="#090d16",
        )
        self.txt_log.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="nsew")

    def _make_card(self, row: int, column: int, title: str):
        card = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        card.grid(row=row, column=column, padx=6, pady=6, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=14, pady=(10, 4))
        stats = ctk.CTkLabel(card, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        stats.pack(anchor="w", padx=14, pady=4)
        return stats

    # --------------------------------------------- Comunicação thread -> UI

    def _append_log(self, text: str) -> None:
        """Registra uma linha no log (thread-safe: só enfileira)."""
        logger.info(text)
        self._ui_queue.put(("log", text))

    def _report_progress(self, index: int, total: int, label: str) -> None:
        """Callback de progresso dos motores (thread-safe)."""
        fraction = index / total if total else 1.0
        text = label if index >= total else f"Etapa {index + 1}/{total}: {label}"
        self._ui_queue.put(("progress", fraction, text))

    def _run_on_ui(self, fn: Callable[[], None]) -> None:
        self._ui_queue.put(("call", fn))

    def _ask_from_worker(self, title: str, message: str) -> bool:
        """Mostra uma pergunta sim/não a partir de uma thread de trabalho e aguarda a resposta."""
        answer = {"value": False}
        done = threading.Event()

        def ask() -> None:
            try:
                answer["value"] = messagebox.askyesno(title, message, icon="warning", parent=self)
            finally:
                done.set()

        self._run_on_ui(ask)
        done.wait()
        return answer["value"]

    def _process_ui_queue(self) -> None:
        """Consome a fila na thread principal, inserindo logs em lote."""
        pending_logs = []
        try:
            for _ in range(1000):
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    pending_logs.append(item[1])
                    continue
                if pending_logs:
                    self._flush_logs(pending_logs)
                    pending_logs = []
                if kind == "progress":
                    self.progress_bar.set(item[1])
                    self._status_text = item[2]
                    self._refresh_status()
                elif kind == "call":
                    item[1]()
        except queue.Empty:
            pass
        finally:
            if pending_logs:
                self._flush_logs(pending_logs)
            self.after(50, self._process_ui_queue)

    def _flush_logs(self, lines) -> None:
        self._log_history.extend(lines)
        self.txt_log.insert("end", "\n".join(lines) + "\n")
        line_count = int(self.txt_log.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            self.txt_log.delete("1.0", f"{line_count - MAX_LOG_LINES}.0")
        self.txt_log.see("end")

    def _refresh_status(self) -> None:
        text = self._status_text
        if self._busy:
            elapsed = int(time.monotonic() - self._busy_since)
            text += f"   ({elapsed // 60:02d}:{elapsed % 60:02d})"
            if self._cancel_event is not None and self._cancel_event.is_set():
                text += " — cancelando após a etapa atual..."
        self.lbl_status.configure(text=text)

    def _tick_elapsed(self) -> None:
        if self._busy:
            self._refresh_status()
        self.after(1000, self._tick_elapsed)

    # ------------------------------------------------------- Estado da UI

    def _set_busy(self, busy: bool, cancellable: bool = False) -> None:
        self._busy = busy
        idle = "disabled" if busy else "normal"
        self.btn_analyze.configure(state=idle)
        self.btn_report.configure(state=idle)
        self.btn_fix.configure(state="normal" if (not busy and self.last_diagnostic) else "disabled")
        if busy and cancellable:
            self.btn_cancel.configure(state="normal")
            self.btn_cancel.grid()
        else:
            self.btn_cancel.grid_remove()
        for chk, admin_only in self.fix_checkboxes.values():
            chk.configure(state="disabled" if (busy or admin_only) else "normal")
        if self.is_elevated:
            self.chk_deep_sfc.configure(state=idle)
        if busy:
            self._busy_since = time.monotonic()
            self.progress_bar.set(0)
        else:
            self._cancel_event = None
        self._refresh_status()

    def _trigger(self, button, action: Callable[[], None]) -> None:
        """Atalho de teclado: só executa se o botão correspondente estiver habilitado."""
        if button.cget("state") == "normal":
            action()

    def _run_task(self, task: Callable, on_success: Callable, cancellable: bool = False) -> None:
        """Executa `task` em thread de trabalho; erros são logados e exibidos ao usuário."""
        self._set_busy(True, cancellable)

        def worker() -> None:
            try:
                result = task()
                self._run_on_ui(lambda: on_success(result))
            except Exception as exc:
                logger.exception("Erro na operação em segundo plano")
                msg = f"{type(exc).__name__}: {exc}"
                self._append_log(f"[ERRO] A operação falhou: {msg}")
                self._run_on_ui(lambda: messagebox.showerror(
                    "Erro", f"A operação falhou:\n\n{msg}\n\nDetalhes no log: {self.log_path or 'console'}", parent=self))
            finally:
                self._run_on_ui(lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def cancel_operation(self) -> None:
        if self._cancel_event is not None and not self._cancel_event.is_set():
            self._cancel_event.set()
            self.btn_cancel.configure(state="disabled")
            self._append_log("[!] Cancelamento solicitado — a etapa atual será concluída antes de parar.")
            self._refresh_status()

    def _on_close(self) -> None:
        if self._busy and not messagebox.askyesno(
            "Operação em andamento",
            "Há uma operação em andamento. Se fechar agora, ferramentas como SFC, DISM ou "
            "instaladores podem continuar rodando em segundo plano.\n\nFechar mesmo assim?",
            icon="warning", parent=self,
        ):
            return
        self.destroy()

    def report_callback_exception(self, exc, val, tb) -> None:
        """Erros em callbacks do Tkinter: registra no log em vez de sumir silenciosamente."""
        logger.error("Erro na interface", exc_info=(exc, val, tb))
        messagebox.showerror("Erro inesperado", f"{exc.__name__}: {val}", parent=self)

    # ------------------------------------------------------- Fase 1: Análise

    def start_analysis_thread(self) -> None:
        """Inicia a Análise da Fase 1 em uma thread separada."""
        run_sfc = bool(self.chk_deep_sfc.get()) and self.is_elevated
        self._status_text = "Analisando o sistema..."
        self._run_task(
            lambda: self.diagnostic_engine.run_full_diagnosis(run_sfc=run_sfc, elevated=self.is_elevated),
            self._on_analysis_done,
        )

    def _on_analysis_done(self, result: DiagnosticResult) -> None:
        self.last_diagnostic = result
        self.last_fix_report = None
        self._update_cards_with_results(result)
        self._status_text = f"Análise concluída: {result.total_issues_found} problema(s) encontrado(s)"
        self._refresh_status()

    def _update_cards_with_results(self, res: DiagnosticResult) -> None:
        """Atualiza os cards da interface com os dados medidos (N/D quando não medido)."""
        cpu_text = f"CPU: {res.cpu_usage_percent:.1f}% ({res.cpu_cores_physical}C/{res.cpu_cores_logical}T)\n"
        cpu_text += f"RAM: {res.ram_used_gb:.1f}GB / {res.ram_total_gb:.1f}GB ({res.ram_usage_percent:.1f}%)\n"
        if res.top_cpu_processes:
            top_p = res.top_cpu_processes[0]
            cpu_text += f"Maior consumidor: {top_p.name} ({top_p.cpu_percent:.1f}%)"
        if res.offending_processes:
            cpu_text += f"\nGargalo causado por: {', '.join(p.name for p in res.offending_processes)}"
        self.lbl_cpu_stats.configure(text=cpu_text)

        disk_text = ""
        for d in res.disks[:2]:
            disk_text += f"{d['drive']} {d['free_gb']}GB livres ({d['used_percent']}% usado)\n"
        disk_text += f"Temp (>24h): {res.temp_files_size_mb} MB ({res.temp_files_count} arquivos)\n"
        disk_text += f"Saúde: {res.smart_status} · {res.system_drive_media}"
        self.lbl_disk_stats.configure(text=disk_text)

        if res.ping_latency_ms is not None:
            latency = f"{res.ping_latency_ms:.0f} ms" + (" (TCP)" if res.latency_method.startswith("TCP") else "")
        else:
            latency = "N/D"
        loss = f"{res.packet_loss_percent:.0f}%" if res.packet_loss_percent is not None else "N/D"
        dns = "OK" if res.dns_ok else "Falhou" if res.dns_ok is False else "N/D"
        net_text = f"Status: {'Conectado' if res.network_online else 'Sem Internet'} · DNS: {dns}\n"
        net_text += f"Latência: {latency}\n"
        net_text += f"Perda de Pacotes: {loss}\n"
        net_text += f"Adaptadores Ativos: {len(res.network_adapters)}"
        self.lbl_net_stats.configure(text=net_text)

        image = {"Healthy": "Saudável", "Repairable": "Precisa de reparo", "NonRepairable": "Não reparável"}
        os_text = f"Imagem (DISM): {image.get(res.image_health, 'N/D')}\n"
        if res.sfc_integrity_ok is None:
            os_text += "SFC: Não verificado\n"
        else:
            os_text += f"SFC: {'OK' if res.sfc_integrity_ok else 'Violações detectadas'}\n"
        if res.stopped_services:
            first = res.stopped_services[0]
            os_text += f"Serviços com problema: {len(res.stopped_services)}\nEx: {first['display'][:28]} ({first['problem']})"
        else:
            os_text += "Serviços essenciais: OK"
        self.lbl_os_stats.configure(text=os_text)

    # ------------------------------------------------------- Fase 2: Auto-Fix

    def _collect_options(self) -> FixOptions:
        values = {key: bool(chk.get()) and not admin_only for key, (chk, admin_only) in self.fix_checkboxes.items()}
        return FixOptions(**values)

    def start_autofix_thread(self) -> None:
        """Confirma o plano com o usuário e inicia a Fase 2 em uma thread separada."""
        diag = self.last_diagnostic
        if diag is None:
            messagebox.showinfo("Análise necessária", "Execute a análise (F1) antes de aplicar correções.", parent=self)
            return

        options = self._collect_options()
        if not any(vars(options).values()):
            messagebox.showinfo("Nenhuma ação", "Selecione ao menos uma opção de reparo.", parent=self)
            return

        plan = describe_plan(options, diag)
        age_min = (datetime.datetime.now() - diag.analyzed_at).total_seconds() / 60 if diag.analyzed_at else 0
        header = ""
        if age_min > STALE_ANALYSIS_MINUTES:
            header = f"Atenção: a análise foi feita há {age_min:.0f} minutos. Considere refazê-la.\n\n"
        if not messagebox.askyesno(
            "Confirmar correções",
            header + "As seguintes ações serão executadas:\n\n" + "\n".join(plan) + "\n\nDeseja continuar?",
            icon="warning", parent=self,
        ):
            self._append_log("[*] Correções canceladas pelo usuário.")
            return

        cancel_event = threading.Event()
        self._cancel_event = cancel_event
        self._status_text = "Aplicando correções..."
        self._run_task(
            lambda: self.fix_engine.run_auto_fix(diag, options, cancel_event),
            self._on_fix_done,
            cancellable=True,
        )

    def _on_fix_done(self, report: FixReport) -> None:
        self.last_fix_report = report
        errors = report.errors
        self._append_log(
            f"\n[RESUMO] {len(report.steps)} etapa(s) · {len(errors)} erro(s) · "
            f"{report.temp_files_deleted} arquivos removidos ({report.temp_space_freed_mb} MB)"
        )
        if report.killed_processes:
            self._append_log(f"- Processos Encerrados: {', '.join(report.killed_processes)}")

        if report.aborted_reason:
            title, msg = "Correções interrompidas", report.aborted_reason
        elif report.cancelled:
            title, msg = "Correções canceladas", "A operação foi cancelada. Veja o log para as etapas concluídas."
        elif errors:
            title, msg = "Concluído com erros", "Algumas etapas falharam:\n\n" + "\n".join(errors[:8])
        else:
            title, msg = "Concluído", "Todas as correções selecionadas foram aplicadas."
        if report.reboot_required:
            msg += "\n\nREINICIE o computador para concluir os reparos."
        self._status_text = title
        self._refresh_status()
        (messagebox.showwarning if (errors or report.reboot_required) else messagebox.showinfo)(title, msg, parent=self)

    # ------------------------------------------------------------- Relatório

    def export_report(self) -> None:
        """Gera um relatório em TXT com a última análise, as correções aplicadas e o log."""
        if not self.last_diagnostic:
            messagebox.showinfo("Relatório", "Faça uma análise primeiro para gerar o relatório.", parent=self)
            return

        file_path = fd.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            initialfile=f"Relatorio_PC_Health_{datetime.datetime.now():%Y%m%d_%H%M}.txt",
            title="Salvar Relatório",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
        )
        if not file_path:
            return

        content = build_text_report(
            self.last_diagnostic, self.last_fix_report, "\n".join(self._log_history), self.log_path)
        try:
            with open(file_path, "w", encoding="utf-8-sig") as f:  # BOM: o Bloco de Notas antigo exibe acentos corretamente
                f.write(content)
            self._append_log(f"[OK] Relatório salvo com sucesso em: {file_path}")
        except OSError as e:
            self._append_log(f"[-] Erro ao salvar o relatório: {e}")
            messagebox.showerror("Relatório", f"Não foi possível salvar o relatório:\n{e}", parent=self)


if __name__ == "__main__":
    app = PCHealthApp(is_elevated=True)
    app.mainloop()
