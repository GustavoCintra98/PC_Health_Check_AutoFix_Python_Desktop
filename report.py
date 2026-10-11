"""
PC Health Check & Auto-Fix - Geração de relatório em texto.

Função pura (sem dependência da interface) para facilitar testes.
"""

import datetime
from typing import Optional

from diagnostics import DiagnosticResult
from fixer import FixReport

_STATUS_LABEL = {"ok": "OK", "warning": "AVISO", "error": "ERRO", "skipped": "IGNORADO"}


def _na(value, fmt: str = "{}", default: str = "N/D") -> str:
    return default if value is None else fmt.format(value)


def build_text_report(
    diag: DiagnosticResult,
    fix: Optional[FixReport] = None,
    log_text: str = "",
    log_file: Optional[str] = None,
) -> str:
    sep = "-" * 60
    out = [
        "=== RELATÓRIO DO PC HEALTH CHECK ===",
        f"Gerado em: {datetime.datetime.now():%d/%m/%Y %H:%M:%S}",
        f"Análise realizada em: {diag.analyzed_at:%d/%m/%Y %H:%M:%S}" if diag.analyzed_at else "Análise: N/D",
        f"Privilégios: {'Administrador' if diag.elevated else 'Usuário padrão (verificações limitadas)'}",
        sep,
        "",
        "[CPU E MEMÓRIA]",
        f"CPU: {diag.cpu_usage_percent:.1f}% ({diag.cpu_cores_physical} núcleos / {diag.cpu_cores_logical} threads)",
        f"RAM: {diag.ram_used_gb:.1f} GB de {diag.ram_total_gb:.1f} GB ({diag.ram_usage_percent:.1f}%)",
    ]
    for p in diag.top_ram_processes:
        out.append(f"  - {p.name} (PID {p.pid}): {p.memory_mb:.0f} MB, CPU {p.cpu_percent:.1f}%")

    out += ["", "[ARMAZENAMENTO]"]
    for d in diag.disks:
        out.append(f"{d['drive']} {d['free_gb']} GB livres de {d['total_gb']} GB ({d['used_percent']}% usado)")
    for pd in diag.physical_disks:
        out.append(f"Disco físico: {pd['name']} — {pd['media']} — {pd['health']}")
    out += [
        f"Saúde (S.M.A.R.T.): {diag.smart_status}",
        f"Fragmentação: {diag.fragmentation_status}",
        f"Temporários elegíveis: {diag.temp_files_size_mb} MB ({diag.temp_files_count} arquivos)",
        "",
        "[REDE]",
        f"Internet: {'Conectado' if diag.network_online else 'Sem conexão'}",
        f"Latência: {_na(diag.ping_latency_ms, '{:.0f} ms')} {('(' + diag.latency_method + ')') if diag.latency_method else ''}".rstrip(),
        f"Perda de pacotes: {_na(diag.packet_loss_percent, '{:.0f}%')}",
        f"DNS: {'OK' if diag.dns_ok else 'Falhou' if diag.dns_ok is False else 'N/D'}",
        "",
        "[SISTEMA OPERACIONAL]",
        f"Imagem do Windows (DISM): {_na(diag.image_health)}",
        f"SFC: {diag.sfc_details}",
    ]
    for s in diag.all_services_status:
        problem = f" — {s['problem']}" if s.get("problem") else ""
        out.append(f"  - {s['display']}: {s['status']} / {s['start_type']}{problem}")

    out += ["", f"[PROBLEMAS DETECTADOS: {diag.total_issues_found}]"]
    out += [f"- {issue}" for issue in diag.issues_list] or ["Nenhum problema detectado."]

    if fix is not None:
        out += ["", sep, "[CORREÇÕES APLICADAS]"]
        if fix.aborted_reason:
            out.append(f"Interrompido: {fix.aborted_reason}")
        if fix.cancelled:
            out.append("Operação cancelada pelo usuário antes de concluir todas as etapas.")
        for step in fix.steps:
            out.append(f"[{_STATUS_LABEL.get(step.status, step.status)}] {step.name}: {step.detail}")
        if fix.reboot_required:
            out.append("*** É NECESSÁRIO REINICIAR O COMPUTADOR PARA CONCLUIR OS REPAROS ***")

    out += ["", sep, "[LOG DO TERMINAL]", log_text.rstrip()]
    if log_file:
        out.append(f"\nLog completo: {log_file}")
    return "\n".join(out) + "\n"
