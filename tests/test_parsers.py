"""Testes dos parsers de saída das ferramentas do Windows (pt-BR e en-US)."""

import pytest

from diagnostics import (
    ProcessInfo, classify_service, parse_defrag_output, parse_ping_output,
    parse_sfc_output, select_offenders,
)

PING_PT = """
Disparando 8.8.8.8 com 32 bytes de dados:
Resposta de 8.8.8.8: bytes=32 tempo=9ms TTL=115
Resposta de 8.8.8.8: bytes=32 tempo=12ms TTL=115

Estatísticas do Ping para 8.8.8.8:
    Pacotes: Enviados = 4, Recebidos = 3, Perdidos = 1 (25% de perda),
Aproximar um número redondo de vezes em milissegundos:
    Mínimo = 9ms, Máximo = 12ms, Média = 10ms
"""

PING_EN = """
Pinging 8.8.8.8 with 32 bytes of data:
Reply from 8.8.8.8: bytes=32 time=21ms TTL=115

Ping statistics for 8.8.8.8:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 20ms, Maximum = 25ms, Average = 22ms
"""

PING_TIMEOUT_PT = """
Disparando 8.8.8.8 com 32 bytes de dados:
Esgotado o tempo limite do pedido.

Estatísticas do Ping para 8.8.8.8:
    Pacotes: Enviados = 4, Recebidos = 0, Perdidos = 4 (100% de perda),
"""


def test_ping_pt_br():
    assert parse_ping_output(PING_PT) == (10.0, 25.0)


def test_ping_en_us():
    assert parse_ping_output(PING_EN) == (22.0, 0.0)


def test_ping_pt_br_mojibake_still_parses():
    # Saída OEM decodificada com o codec errado (bug original): o parser não depende dos acentos
    broken = PING_PT.replace("Média", "M‚dia").replace("Mínimo", "M¡nimo").replace("Máximo", "M\xa0ximo")
    assert parse_ping_output(broken) == (10.0, 25.0)


def test_ping_timeout_has_no_fake_latency():
    assert parse_ping_output(PING_TIMEOUT_PT) == (None, 100.0)


def test_ping_empty_output():
    assert parse_ping_output("") == (None, None)


@pytest.mark.parametrize("output, expected", [
    ("Windows Resource Protection did not find any integrity violations.", "ok"),
    ("A Proteção de Recursos do Windows não encontrou nenhuma violação de integridade.", "ok"),
    ("Windows Resource Protection found integrity violations.", "violations"),
    ("A Proteção de Recursos do Windows encontrou violações de integridade.", "violations"),
    ("Windows Resource Protection found corrupt files and successfully repaired them.", "repaired"),
    ("A Proteção de Recursos do Windows encontrou arquivos corrompidos e os reparou com êxito.", "repaired"),
    ("Windows Resource Protection found corrupt files but was unable to fix some of them.", "unrepairable"),
    ("A Proteção de Recursos do Windows encontrou arquivos corrompidos, mas não pôde corrigir alguns deles.",
     "unrepairable"),
    ("Windows Resource Protection could not perform the requested operation.", None),
    ("", None),
])
def test_parse_sfc(output, expected):
    assert parse_sfc_output(output) == expected


def test_sfc_utf16_roundtrip():
    raw = "Verificação 100% concluída.\r\n\r\nA Proteção de Recursos do Windows não encontrou nenhuma violação de integridade.\r\n"
    decoded = raw.encode("utf-16-le").decode("utf-16-le")
    assert parse_sfc_output(decoded) == "ok"


def test_parse_defrag():
    out_en = "Volume Information:\n    Volume size = 931 GB\n    Free space = 400 GB\n    Total fragmented space = 14%\n"
    out_pt = "Informações do volume:\n    Espaço livre = 400 GB\n    Espaço total fragmentado = 3%\n"
    assert parse_defrag_output(out_en) == 14
    assert parse_defrag_output(out_pt) == 3
    assert parse_defrag_output("You do not need to defragment this volume.") is None


@pytest.mark.parametrize("status, start_type, problem", [
    ("stopped", "manual", None),            # wuauserv/BITS ociosos: normal
    ("running", "automatic", None),
    ("stopped", "automatic", "parado (início automático)"),
    ("stopped", "disabled", "desativado"),
    ("running", "disabled", "desativado"),
])
def test_classify_service(status, start_type, problem):
    assert classify_service(status, start_type) == problem


def _proc(pid, name, cpu=0.0, mem_pct=0.0, critical=False):
    return ProcessInfo(pid=pid, name=name, cpu_percent=cpu, memory_mb=mem_pct * 100,
                       memory_percent=mem_pct, is_critical=critical, create_time=1.0)


def test_select_offenders_requires_bottleneck():
    procs = [_proc(100, "chrome.exe", cpu=50, mem_pct=30)]
    assert select_offenders(procs, cpu_bottleneck=False, ram_bottleneck=False) == []


def test_select_offenders_ignores_small_and_critical():
    procs = [
        _proc(100, "render.exe", cpu=60),
        _proc(101, "idle.exe", cpu=2),
        _proc(102, "svchost.exe", cpu=90, critical=True),
        _proc(103, "bigmem.exe", mem_pct=40),
    ]
    cpu_only = select_offenders(procs, cpu_bottleneck=True, ram_bottleneck=False)
    assert [p.name for p in cpu_only] == ["render.exe"]
    both = select_offenders(procs, cpu_bottleneck=True, ram_bottleneck=True)
    assert sorted(p.name for p in both) == ["bigmem.exe", "render.exe"]
