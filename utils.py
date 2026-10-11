"""
PC Health Check & Auto-Fix - Utilitários compartilhados.

Centraliza o que antes estava duplicado entre os motores:
- Execução de comandos externos com o encoding correto do Windows
  (OEM para ferramentas de console, UTF-16 para o sfc), timeout e sem janela.
- Execução de scripts PowerShell via -EncodedCommand (sem problemas de aspas).
- Varredura segura de diretórios temporários (não atravessa junctions/symlinks).
- Inicialização de COM por thread para uso do WMI.
- Configuração de log em arquivo.
"""

import base64
import io
import logging
import os
import stat
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Callable, Iterator, List, Optional, Sequence, Tuple

try:
    import pythoncom
except ImportError:
    pythoncom = None

APP_NAME = "PCHealthCheck"

# Ferramentas de console (ping, ipconfig, netsh, sc, dism, defrag) escrevem na
# página de código OEM (cp850 em pt-BR); decodificar como cp1252 corrompe acentos.
OEM_ENCODING = "oem" if sys.platform == "win32" else "utf-8"
# O sfc.exe escreve em UTF-16 LE quando a saída é redirecionada.
SFC_ENCODING = "utf-16-le"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

logger = logging.getLogger(APP_NAME)


# ---------------------------------------------------------------------------
# Execução de comandos
# ---------------------------------------------------------------------------

@dataclass
class CmdResult:
    """Resultado da execução de um comando externo."""
    returncode: Optional[int]
    output: str
    timed_out: bool = False
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_cmd(args: Sequence[str], timeout: float = 60, encoding: str = OEM_ENCODING) -> CmdResult:
    """
    Executa um comando e devolve código de saída + saída combinada (stdout/stderr).

    Nunca lança exceção: comando inexistente, timeout ou erro de SO viram um
    CmdResult com returncode=None e o campo `error` preenchido.
    """
    try:
        proc = subprocess.run(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            creationflags=NO_WINDOW,
        )
        return CmdResult(proc.returncode, proc.stdout.decode(encoding, errors="replace"))
    except subprocess.TimeoutExpired as e:
        partial = (e.output or b"").decode(encoding, errors="replace")
        return CmdResult(None, partial, timed_out=True, error=f"tempo limite de {timeout:.0f}s excedido")
    except (OSError, ValueError) as e:
        return CmdResult(None, "", error=str(e))


def stream_cmd(
    args: Sequence[str],
    on_line: Callable[[str], None],
    timeout: Optional[float] = None,
    encoding: str = OEM_ENCODING,
) -> CmdResult:
    """
    Executa um comando enviando cada linha de saída para `on_line` em tempo real.

    Linhas terminadas em '\\r' (barras de progresso) também são entregues como
    linhas separadas. Se `timeout` for excedido o processo é encerrado.
    A saída completa é devolvida em CmdResult.output para análise posterior.
    """
    try:
        proc = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=NO_WINDOW,
        )
    except (OSError, ValueError) as e:
        return CmdResult(None, "", error=str(e))

    timed_out = threading.Event()

    def _watchdog() -> None:
        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if time.monotonic() > deadline:
                timed_out.set()
                proc.kill()
                return
            time.sleep(0.5)

    if timeout:
        threading.Thread(target=_watchdog, daemon=True).start()

    collected: List[str] = []
    reader = io.TextIOWrapper(proc.stdout, encoding=encoding, errors="replace", newline=None)
    for line in reader:
        clean = line.strip().strip("\x00")
        if clean:
            collected.append(clean)
            on_line(clean)
    proc.wait()

    if timed_out.is_set():
        return CmdResult(None, "\n".join(collected), timed_out=True,
                         error=f"tempo limite de {timeout:.0f}s excedido")
    return CmdResult(proc.returncode, "\n".join(collected))


def run_powershell(script: str, timeout: float = 120) -> CmdResult:
    """
    Executa um script do Windows PowerShell 5.1 via -EncodedCommand.

    - A saída é forçada para UTF-8, evitando a página de código OEM.
    - Erros viram uma última linha "ERROR|mensagem" (em vez do CLIXML que o
      PowerShell escreve no stderr) e preenchem CmdResult.error.
    """
    wrapped = (
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
        "$ProgressPreference = 'SilentlyContinue'\n"
        "$ErrorActionPreference = 'Stop'\n"
        "try {\n" + script + "\n} catch { 'ERROR|' + $_.Exception.Message; exit 1 }\n"
    )
    encoded = base64.b64encode(wrapped.encode("utf-16-le")).decode("ascii")
    res = run_cmd(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-EncodedCommand", encoded],
        timeout=timeout,
        encoding="utf-8",
    )
    lines = res.output.strip().splitlines()
    if lines and lines[-1].startswith("ERROR|"):
        res.error = lines[-1][len("ERROR|"):].strip()
    return res


# ---------------------------------------------------------------------------
# Sistema de arquivos
# ---------------------------------------------------------------------------

def get_temp_dirs() -> List[str]:
    """Diretórios temporários do usuário atual e do Windows (sem duplicatas)."""
    candidates = [
        os.environ.get("TEMP"),
        os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"),
    ]
    seen, result = set(), []
    for path in candidates:
        if not path:
            continue
        norm = os.path.normcase(os.path.abspath(path))
        if norm not in seen and os.path.isdir(path):
            seen.add(norm)
            result.append(path)
    return result


def get_protected_paths() -> List[str]:
    """Caminhos que a limpeza nunca deve tocar (ex.: extração do próprio .exe do PyInstaller)."""
    protected = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        protected.append(os.path.normcase(os.path.abspath(meipass)))
    return protected


def is_reparse_point(entry: os.DirEntry) -> bool:
    """True para symlinks, junctions e outros reparse points do NTFS."""
    try:
        if entry.is_symlink():
            return True
        attrs = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
        return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
    except OSError:
        return True  # na dúvida, trata como link e não entra


def iter_old_files(
    root: str,
    min_age_hours: float,
    protected: Sequence[str] = (),
) -> Iterator[Tuple[str, int]]:
    """
    Percorre `root` recursivamente devolvendo (caminho, tamanho) de arquivos
    modificados há mais de `min_age_hours`.

    Diferente de os.walk(topdown=False), NÃO entra em junctions/symlinks:
    executando como Administrador, seguir uma junction plantada em
    C:\\Windows\\Temp permitiria apagar arquivos fora da pasta temporária.
    """
    cutoff = time.time() - min_age_hours * 3600
    stack = [root]
    while stack:
        current = stack.pop()
        if os.path.normcase(os.path.abspath(current)) in protected:
            continue
        try:
            with os.scandir(current) as it:
                entries = list(it)
        except OSError:
            continue
        for entry in entries:
            if is_reparse_point(entry):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    st = entry.stat(follow_symlinks=False)
                    if st.st_mtime < cutoff:
                        yield entry.path, st.st_size
            except OSError:
                continue


def remove_empty_dirs(root: str, min_age_hours: float = 0, protected: Sequence[str] = ()) -> None:
    """
    Remove subdiretórios vazios de `root` (sem entrar em reparse points).
    Pastas modificadas há menos de `min_age_hours` são mantidas, pois podem ter
    acabado de ser criadas por um instalador em execução.
    """
    cutoff = time.time() - min_age_hours * 3600
    try:
        with os.scandir(root) as it:
            entries = list(it)
    except OSError:
        return
    for entry in entries:
        try:
            if is_reparse_point(entry) or not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        if os.path.normcase(os.path.abspath(entry.path)) in protected:
            continue
        remove_empty_dirs(entry.path, min_age_hours, protected)
        try:
            if os.stat(entry.path).st_mtime < cutoff:
                os.rmdir(entry.path)
        except OSError:
            pass


def delete_file(path: str) -> bool:
    """Apaga um arquivo (removendo o atributo somente-leitura se preciso). Retorna False se estiver em uso."""
    try:
        os.remove(path)
        return True
    except PermissionError:
        try:
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
            return True
        except OSError:
            return False
    except OSError:
        return False


# ---------------------------------------------------------------------------
# COM / WMI
# ---------------------------------------------------------------------------

@contextmanager
def com_initialized() -> Iterator[None]:
    """
    Inicializa COM na thread atual. Objetos WMI pertencem à thread que os criou,
    então cada thread de trabalho precisa do seu próprio CoInitialize/CoUninitialize.
    """
    if pythoncom is None:
        yield
        return
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


# ---------------------------------------------------------------------------
# Log em arquivo
# ---------------------------------------------------------------------------

def get_log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME, "logs")


def setup_logging() -> str:
    """Configura log rotativo em %LOCALAPPDATA%\\PCHealthCheck\\logs\\app.log e devolve o caminho."""
    log_dir = get_log_dir()
    log_path = os.path.join(log_dir, "app.log")
    if logger.handlers:
        return log_path
    logger.setLevel(logging.INFO)
    try:
        os.makedirs(log_dir, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return log_path
