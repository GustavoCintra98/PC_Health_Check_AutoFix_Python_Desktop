"""Testes do motor de correção (sem executar comandos destrutivos)."""

import dataclasses
import threading

import fixer
from diagnostics import DiagnosticResult, ProcessInfo
from fixer import AutoFixEngine, FixOptions, FixReport, describe_plan
from report import build_text_report
from utils import CmdResult


def test_fixreport_fields_are_dataclass_fields():
    names = {f.name for f in dataclasses.fields(FixReport)}
    assert "restore_point_created" in names
    assert "bool" not in FixReport.__dict__  # bug antigo: `restore_point_created = bool = False`


def _healthy_diag(**kwargs):
    base = dict(elevated=True, network_online=True, dns_ok=True, packet_loss_percent=0.0,
                ping_latency_ms=10.0, image_health="Healthy")
    base.update(kwargs)
    return DiagnosticResult(**base)


def test_network_repair_not_run_when_unchecked(monkeypatch):
    """Bug antigo: sem análise prévia, o reparo de rede rodava mesmo com a opção desmarcada."""
    called = []
    engine = AutoFixEngine()
    monkeypatch.setattr(engine, "repair_network", lambda *a: called.append("net"))
    options = FixOptions(create_restore=False, clean_temp=False, fix_network=False, fix_os=False)
    engine.run_auto_fix(DiagnosticResult(network_online=False, elevated=True), options)
    assert called == []


def test_admin_only_steps_skipped_without_elevation(monkeypatch):
    engine = AutoFixEngine()
    monkeypatch.setattr(engine, "repair_os_integrity", lambda *a: (_ for _ in ()).throw(AssertionError("não deveria rodar")))
    options = FixOptions(create_restore=True, clean_temp=False, fix_network=False, fix_os=True)
    report = engine.run_auto_fix(_healthy_diag(elevated=False), options)
    assert all(s.status == "skipped" for s in report.steps)


def test_restore_point_failure_asks_user_and_aborts(monkeypatch):
    asked = []
    engine = AutoFixEngine(confirm_callback=lambda title, msg: asked.append(title) or False)
    monkeypatch.setattr(engine, "create_restore_point", lambda report: False)
    monkeypatch.setattr(engine, "clean_storage", lambda report: (_ for _ in ()).throw(AssertionError("não deveria rodar")))
    report = engine.run_auto_fix(_healthy_diag(), FixOptions(create_restore=True, clean_temp=True,
                                                             fix_network=False, fix_os=False))
    assert asked and report.aborted_reason


def test_cancel_between_steps(monkeypatch):
    engine = AutoFixEngine()
    cancel = threading.Event()
    ran = []

    def first(report):
        ran.append("temp")
        cancel.set()

    monkeypatch.setattr(engine, "clean_storage", first)
    monkeypatch.setattr(engine, "empty_recycle_bin", lambda report: ran.append("bin"))
    options = FixOptions(create_restore=False, clean_temp=True, empty_recycle_bin=True, fix_network=False, fix_os=False)
    report = engine.run_auto_fix(_healthy_diag(), options, cancel)
    assert ran == ["temp"] and report.cancelled


def test_step_exception_does_not_stop_others(monkeypatch):
    engine = AutoFixEngine()
    ran = []
    monkeypatch.setattr(engine, "clean_storage", lambda report: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(engine, "empty_recycle_bin", lambda report: ran.append("bin"))
    options = FixOptions(create_restore=False, clean_temp=True, empty_recycle_bin=True, fix_network=False, fix_os=False)
    report = engine.run_auto_fix(_healthy_diag(), options)
    assert ran == ["bin"]
    assert any("boom" in e for e in report.errors)


def test_network_repair_stops_at_dns_when_healthy(monkeypatch):
    commands = []
    monkeypatch.setattr(fixer, "run_cmd", lambda args, **kw: commands.append(list(args)) or CmdResult(0, ""))
    report = FixReport()
    AutoFixEngine().repair_network(report, _healthy_diag())
    assert commands == [["ipconfig", "/flushdns"]]
    assert not report.reboot_required


def test_kill_skips_reused_pid(monkeypatch):
    class FakeProc:
        def __init__(self, pid):
            self.pid = pid

        def name(self):
            return "outro.exe"

        def create_time(self):
            return 999.0

        def terminate(self):
            raise AssertionError("não deveria encerrar um PID reutilizado")

    monkeypatch.setattr(fixer.psutil, "Process", FakeProc)
    monkeypatch.setattr(fixer, "own_process_tree_pids", lambda: set())
    report = FixReport()
    info = ProcessInfo(pid=4242, name="chrome.exe", cpu_percent=90, memory_mb=100,
                       memory_percent=1, is_critical=False, create_time=1.0)
    AutoFixEngine().kill_offending_processes(report, [info])
    assert report.killed_processes == []


def test_deletion_progress_is_throttled_by_time(monkeypatch):
    """Exclusões longas devem mostrar andamento, mas sem uma linha de log por arquivo."""
    clock = [0.0]
    monkeypatch.setattr(fixer.time, "monotonic", lambda: clock[0])
    lines = []
    progress = fixer._DeletionProgress("Teste", lines.append, interval=3.0)
    for _ in range(1000):  # 1000 arquivos em 1 s: nenhum log
        clock[0] += 0.001
        progress.add(1024 * 1024)
    assert lines == []
    clock[0] = 3.5
    progress.add(1024 * 1024)
    assert progress.deleted == 1001
    assert lines == ["[Teste] 1001 arquivos removidos (1001 MB) até agora..."]
    progress.add(0)  # logo em seguida: ainda dentro do intervalo
    assert len(lines) == 1


def test_describe_plan_mentions_risks():
    diag = _healthy_diag(network_online=False, image_health=None,
                         offending_processes=[ProcessInfo(1234, "app.exe", 90, 10, 1, False, 1.0)])
    options = FixOptions(empty_recycle_bin=True, kill_procs=True)
    text = "\n".join(describe_plan(options, diag))
    assert "LIXEIRA" in text
    assert "app.exe (PID 1234)" in text
    assert "reiniciar" in text
    assert "DISM" in text


def test_report_contains_fix_steps():
    fix = FixReport()
    fix.add("Rede", "ok", "cache DNS limpo")
    fix.reboot_required = True
    text = build_text_report(_healthy_diag(), fix, "linha de log")
    assert "[OK] Rede: cache DNS limpo" in text
    assert "REINICIAR" in text
    assert "linha de log" in text
