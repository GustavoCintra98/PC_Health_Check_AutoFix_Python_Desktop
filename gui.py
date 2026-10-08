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
import tkinter.filedialog as fd

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
        
        # A linha 12 funcionará como uma "mola" elástica para empurrar o que está abaixo dela
        self.sidebar_frame.grid_rowconfigure(12, weight=1) 
        
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="PC Health Check\n& Auto-Fix",
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
            text="  Iniciar Análise (F1)",
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
            text="  Corrigir Tudo (F2)",
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
        self.opt_label.grid(row=4, column=0, padx=20, pady=(12, 4), sticky="w")
        
        # CHECKBOXES (espaçamento pady=2 para ficarem compactos e não apertar a tela)
        self.chk_storage = ctk.CTkCheckBox(self.sidebar_frame, text="Limpar Temp / Lixeira")
        self.chk_storage.select()
        self.chk_storage.grid(row=5, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_network = ctk.CTkCheckBox(self.sidebar_frame, text="Reparar Rede / DNS")
        self.chk_network.select()
        self.chk_network.grid(row=6, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_os = ctk.CTkCheckBox(self.sidebar_frame, text="SFC / DISM & Serviços")
        self.chk_os.select()
        self.chk_os.grid(row=7, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_procs = ctk.CTkCheckBox(self.sidebar_frame, text="Matar Processos Gargalo")
        self.chk_procs.grid(row=8, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_restore = ctk.CTkCheckBox(self.sidebar_frame, text="Criar Ponto Restauração")
        self.chk_restore.select()
        self.chk_restore.grid(row=9, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_winget = ctk.CTkCheckBox(self.sidebar_frame, text="Atualizar Apps (Winget)")
        self.chk_winget.grid(row=10, column=0, padx=20, pady=2, sticky="w")
        
        self.chk_wupdate = ctk.CTkCheckBox(self.sidebar_frame, text="Reparar WinUpdate")
        self.chk_wupdate.grid(row=11, column=0, padx=20, pady=2, sticky="w")
        
        # Botão Gerar Relatório na Linha 13
        self.btn_report = ctk.CTkButton(
            self.sidebar_frame,
            text="  Gerar Relatório",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            command=self.export_report
        )
        self.btn_report.grid(row=13, column=0, padx=20, pady=(15, 8), sticky="ew")
        
        # Label de versão na Linha 14
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="v2.5 Professional\nWindows 10/11 x64",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        self.version_label.grid(row=14, column=0, padx=20, pady=16)

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

        self.chk_restore = ctk.CTkCheckBox(self.sidebar_frame, text="Criar Ponto de Restauração")
        self.chk_restore.select()
        self.chk_restore.grid(row=8, column=0, padx=20, pady=4, sticky="w")

        self.chk_winget = ctk.CTkCheckBox(self.sidebar_frame, text="Atualizar Apps (Winget)")
        self.chk_winget.grid(row=9, column=0, padx=20, pady=4, sticky="w")

        self.chk_wupdate = ctk.CTkCheckBox(self.sidebar_frame, text="Reparar WinUpdate/Drivers")
        self.chk_wupdate.grid(row=10, column=0, padx=20, pady=4, sticky="w")
        
        # Desloque os botões "Gerar Relatório" e a label de versão para as rows 11 e 12

    def _append_log(self, text: str) -> None:
        """Adiciona linha no console de forma thread-safe."""
        def update():
            self.txt_log.insert("end", text + "\n")
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
        cpu_text = f"CPU: {res.cpu_usage_percent:.1f}% ({res.cpu_cores_physical}C/{res.cpu_cores_logical}T)\n"
        cpu_text += f"RAM: {res.ram_used_gb:.1f}GB / {res.ram_total_gb:.1f}GB ({res.ram_usage_percent:.1f}%)\n"
        if res.top_cpu_processes:
            top_p = res.top_cpu_processes[0]
            cpu_text += f"Maior consumidor: {top_p.name} ({top_p.cpu_percent:.1f}%)"
        self.lbl_cpu_stats.configure(text=cpu_text)

        disk_text = ""
        for d in res.disks[:2]:
            disk_text += f"{d['drive']}: {d['free_gb']}GB livres ({d['used_percent']}%)\n"
        disk_text += f"Temp: {res.temp_files_size_mb} MB ({res.temp_files_count} arquivos)\n"
        disk_text += f"S.M.A.R.T.: {res.smart_status}"
        self.lbl_disk_stats.configure(text=disk_text)

        net_text = f"Status: {'Conectado' if res.network_online else 'Sem Internet'}\n"
        net_text += f"Latência (8.8.8.8): {res.ping_latency_ms or 0:.0f} ms\n"
        net_text += f"Perda de Pacotes: {res.packet_loss_percent:.0f}%\n"
        net_text += f"Adaptadores Ativos: {len(res.network_adapters)}"
        self.lbl_net_stats.configure(text=net_text)

        os_text = f"Integridade SFC: {'OK' if res.sfc_integrity_ok else 'Violações Detectadas'}\n"
        os_text += f"Serviços Parados: {len(res.stopped_services)}\n"
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
        
        # Captura o estado dos checkboxes (Originais)
        do_storage = bool(self.chk_storage.get())
        do_net = bool(self.chk_network.get())
        do_os = bool(self.chk_os.get())
        do_procs = bool(self.chk_procs.get())
        
        # Captura o estado dos novos checkboxes
        do_restore = bool(self.chk_restore.get())
        do_winget = bool(self.chk_winget.get())
        do_wupdate = bool(self.chk_wupdate.get())

        def worker():
            try:
                diag = self.last_diagnostic or DiagnosticResult()
                self.progress_bar.set(0.3)
                
                # Chamada do motor de correção com todos os parâmetros atualizados
                report = self.fix_engine.run_auto_fix(
                    diag_result=diag,
                    fix_storage=do_storage,
                    fix_os=do_os,
                    fix_network=do_net,
                    kill_procs=do_procs,
                    create_restore=do_restore,
                    update_winget=do_winget,
                    reset_winupdate=do_wupdate
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

    def export_report(self) -> None:
        """Gera um relatório em TXT com os dados da última análise e logs."""
        if not self.last_diagnostic:
            self._append_log("[-] Faça uma análise primeiro para gerar o relatório.")
            return

        file_path = fd.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"Relatorio_PC_Health_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            title="Salvar Relatório",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("=== RELATÓRIO DO PC HEALTH CHECK ===\n")
                f.write(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("-" * 40 + "\n\n")
                
                f.write("[ESTATÍSTICAS DA MÁQUINA]\n")
                f.write(f"CPU: {self.last_diagnostic.cpu_usage_percent:.1f}%\n")
                f.write(f"RAM: {self.last_diagnostic.ram_usage_percent:.1f}% ({self.last_diagnostic.ram_used_gb} GB usados)\n")
                f.write(f"Total de problemas encontrados: {self.last_diagnostic.total_issues_found}\n\n")
                
                if self.last_diagnostic.issues_list:
                    f.write("[PROBLEMAS DETECTADOS]\n")
                    for issue in self.last_diagnostic.issues_list:
                        f.write(f"- {issue}\n")
                    f.write("\n")

                f.write("-" * 40 + "\n")
                f.write("[LOG DO TERMINAL]\n")
                f.write(self.txt_log.get("1.0", "end"))
                
            self._append_log(f"[OK] Relatório salvo com sucesso em: {file_path}")
        except Exception as e:
            self._append_log(f"[-] Erro ao salvar o relatório: {e}")

if __name__ == "__main__":
    app = PCHealthApp(is_elevated=True)
    app.mainloop()
