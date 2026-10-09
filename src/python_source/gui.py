"""
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
        # Configurar Grid principal (Sidebar na esquerda, Conteúdo na direita)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ------------------ BARRA LATERAL (SIDEBAR) ------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        # Logo / Título
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PC Health Check\n& Auto-Fix",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(24, 12))

        # Status de Privilégio UAC
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

        # Separador / Opções de Correção
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

        # Rodapé da Sidebar
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v2.5 Professional\nWindows 10/11 x64",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.version_label.grid(row=9, column=0, padx=20, pady=16)

        # ------------------ ÁREA DE CONTEÚDO PRINCIPAL ------------------
        self.main_content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)

        # Barra de Progresso Superior
        self.progress_bar = ctk.CTkProgressBar(self.main_content, height=8)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.progress_bar.set(0)

        # Painel de Cards de Diagnóstico (Grid 2x2)
        self.cards_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.cards_frame.grid_columnconfigure((0, 1), weight=1)

        # Card 1: CPU e Memória
        self.card_cpu = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_cpu.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        self.lbl_cpu_title = ctk.CTkLabel(self.card_cpu, text="⚙️ CPU & Memória RAM", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_cpu_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_cpu_stats = ctk.CTkLabel(self.card_cpu, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_cpu_stats.pack(anchor="w", padx=14, pady=4)

        # Card 2: Armazenamento & S.M.A.R.T.
        self.card_disk = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_disk.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        self.lbl_disk_title = ctk.CTkLabel(self.card_disk, text="💾 Armazenamento & Disco", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_disk_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_disk_stats = ctk.CTkLabel(self.card_disk, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_disk_stats.pack(anchor="w", padx=14, pady=4)

        # Card 3: Rede & Conectividade
        self.card_net = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_net.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")
        self.lbl_net_title = ctk.CTkLabel(self.card_net, text="🌐 Rede & Conectividade", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_net_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_net_stats = ctk.CTkLabel(self.card_net, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_net_stats.pack(anchor="w", padx=14, pady=4)

        # Card 4: SO & Integridade SFC
        self.card_os = ctk.CTkFrame(self.cards_frame, corner_radius=8)
        self.card_os.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")
        self.lbl_os_title = ctk.CTkLabel(self.card_os, text="🛡️ Sistema & Serviços", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_os_title.pack(anchor="w", padx=14, pady=(10, 4))
        self.lbl_os_stats = ctk.CTkLabel(self.card_os, text="Aguardando verificação...", justify="left", font=ctk.CTkFont(size=12))
        self.lbl_os_stats.pack(anchor="w", padx=14, pady=4)

        # ------------------ CONSOLE DE LOGS EM TEMPO REAL ------------------
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
            self.txt_log.insert("end", text + "\n")
            self.txt_log.see("end")
        self.after(0, update)

    def start_analysis_thread(self) -> None:
        """Inicia a Análise da Fase 1 em uma thread separada para não congelar a GUI."""
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
        """Atualiza o conteúdo visual dos 4 cards de status."""
        # 1. CPU & RAM
        cpu_text = f"CPU: {res.cpu_usage_percent:.1f}% ({res.cpu_cores_physical}C/{res.cpu_cores_logical}T)\n"
        cpu_text += f"RAM: {res.ram_used_gb:.1f}GB / {res.ram_total_gb:.1f}GB ({res.ram_usage_percent:.1f}%)\n"
        if res.top_cpu_processes:
            top_p = res.top_cpu_processes[0]
            cpu_text += f"Maior consumidor: {top_p.name} ({top_p.cpu_percent:.1f}%)"
        self.lbl_cpu_stats.configure(text=cpu_text)

        # 2. Armazenamento
        disk_text = ""
        for d in res.disks[:2]:
            disk_text += f"{d['drive']}: {d['free_gb']}GB livres ({d['used_percent']}%)\n"
        disk_text += f"Temp: {res.temp_files_size_mb} MB ({res.temp_files_count} arquivos)\n"
        disk_text += f"S.M.A.R.T.: {res.smart_status}"
        self.lbl_disk_stats.configure(text=disk_text)

        # 3. Rede
        net_text = f"Status: {'Conectado' if res.network_online else 'Sem Internet'}\n"
        net_text += f"Latência (8.8.8.8): {res.ping_latency_ms or 0:.0f} ms\n"
        net_text += f"Perda de Pacotes: {res.packet_loss_percent:.0f}%\n"
        net_text += f"Adaptadores Ativos: {len(res.network_adapters)}"
        self.lbl_net_stats.configure(text=net_text)

        # 4. SO & Serviços
        os_text = f"Integridade SFC: {'OK' if res.sfc_integrity_ok else 'Violações Detectadas'}\n"
        os_text += f"Serviços Parados: {len(res.stopped_services)}\n"
        if res.stopped_services:
            os_text += f"Ex: {res.stopped_services[0]['display'][:24]}..."
        else:
            os_text += "Todos os serviços essenciais em execução"
        self.lbl_os_stats.configure(text=os_text)

    def start_autofix_thread(self) -> None:
        """Inicia a Fase 2 (Auto-Fix) em uma thread secundária."""
        self.btn_analyze.configure(state="disabled")
        self.btn_fix.configure(state="disabled")
        self.progress_bar.set(0.1)

        do_storage = bool(self.chk_storage.get())
        do_net = bool(self.chk_network.get())
        do_os = bool(self.chk_os.get())
        do_procs = bool(self.chk_procs.get())

        def worker():
            try:
                # Se não rodou análise ainda, cria resultado básico
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
                self._append_log(f"\n[SUCESSO] Auto-Fix Finalizado!\n- Arquivos Deletados: {report.temp_files_deleted} ({report.temp_space_freed_mb} MB)")
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
