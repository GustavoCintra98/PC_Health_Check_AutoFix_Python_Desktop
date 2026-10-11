"""Testes da varredura segura de arquivos e da execução de comandos."""

import os
import subprocess
import sys
import time

import pytest

from utils import delete_file, iter_old_files, remove_empty_dirs, run_cmd

OLD = time.time() - 48 * 3600


def _make_file(path, content=b"x", old=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    if old:
        os.utime(path, (OLD, OLD))


def test_iter_old_files_respects_age(tmp_path):
    _make_file(str(tmp_path / "old.tmp"))
    _make_file(str(tmp_path / "new.tmp"), old=False)
    found = {os.path.basename(p) for p, _ in iter_old_files(str(tmp_path), 24)}
    assert found == {"old.tmp"}


def test_iter_old_files_skips_protected(tmp_path):
    _make_file(str(tmp_path / "_MEI123" / "python313.dll"))
    _make_file(str(tmp_path / "other" / "a.tmp"))
    protected = [os.path.normcase(os.path.abspath(str(tmp_path / "_MEI123")))]
    found = {os.path.basename(p) for p, _ in iter_old_files(str(tmp_path), 24, protected)}
    assert found == {"a.tmp"}


@pytest.mark.skipif(sys.platform != "win32", reason="junctions são específicas do NTFS")
def test_iter_old_files_does_not_follow_junctions(tmp_path):
    temp_dir = tmp_path / "temp"
    outside = tmp_path / "importante"
    _make_file(str(outside / "documento.docx"))
    temp_dir.mkdir()
    link = temp_dir / "armadilha"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)

    found = [p for p, _ in iter_old_files(str(temp_dir), 0)]
    assert found == []

    remove_empty_dirs(str(temp_dir))
    assert (outside / "documento.docx").exists()


def test_remove_empty_dirs_keeps_recent(tmp_path):
    old_dir = tmp_path / "old_empty"
    new_dir = tmp_path / "new_empty"
    old_dir.mkdir()
    new_dir.mkdir()
    os.utime(old_dir, (OLD, OLD))
    remove_empty_dirs(str(tmp_path), min_age_hours=24)
    assert not old_dir.exists()
    assert new_dir.exists()


def test_delete_file_readonly(tmp_path):
    path = tmp_path / "ro.tmp"
    _make_file(str(path))
    os.chmod(path, 0o444)
    assert delete_file(str(path))
    assert not path.exists()


def test_run_cmd_missing_executable():
    res = run_cmd(["comando_que_nao_existe_xyz"])
    assert res.returncode is None
    assert res.error


@pytest.mark.skipif(sys.platform != "win32", reason="teste de encoding OEM do Windows")
def test_run_cmd_decodes_oem_accents():
    res = run_cmd(["cmd", "/c", "echo Média"], encoding="oem")
    # cmd ecoa usando a página OEM; sem o decode correto o "é" vira lixo
    assert res.ok
    assert "M" in res.output and "dia" in res.output
