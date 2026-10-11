"""
PC Health Check & Auto-Fix - Entry Point & UAC Privilege Elevation.

Este módulo é o ponto de entrada principal do aplicativo desktop.
Ele verifica se o processo atual possui privilégios de Administrador
no Windows (necessário para SFC, DISM, reparo de rede e ponto de restauração).
Caso não possua, solicita elevação UAC via ShellExecuteW. Se o usuário recusar,
o aplicativo abre em modo limitado em vez de fechar silenciosamente.

Autor: Senior Infrastructure & Windows Automation Engineer
Licença: MIT
"""

import ctypes
import os
import subprocess
import sys
import threading

from utils import logger, setup_logging

NO_ELEVATE_FLAG = "--no-elevate"


def is_admin() -> bool:
    """
    Verifica se o processo atual possui privilégios administrativos no Windows.

    Returns:
        bool: True se estiver executando como Administrador, False caso contrário.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        # Em ambientes não-Windows de desenvolvimento/teste ou erro na chamada
        return False


def show_error(title: str, message: str) -> None:
    """Exibe erro em caixa de diálogo nativa (o .exe compilado não tem console)."""
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)  # MB_ICONERROR
    except (AttributeError, OSError):
        print(f"{title}: {message}", file=sys.stderr)


def request_admin_elevation() -> bool:
    """
    Reinicia o aplicativo com elevação UAC (verbo 'runas').

    Returns:
        True se a instância elevada foi iniciada (este processo deve encerrar),
        False se o usuário recusou ou a chamada falhou.
    """
    extra_args = [arg for arg in sys.argv[1:] if arg != NO_ELEVATE_FLAG] + [NO_ELEVATE_FLAG]
    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = subprocess.list2cmdline(extra_args)
    else:
        # pythonw.exe evita abrir uma janela de console extra na instância elevada
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        executable = pythonw if os.path.exists(pythonw) else sys.executable
        params = subprocess.list2cmdline([os.path.abspath(sys.argv[0])] + extra_args)

    shell_execute = ctypes.windll.shell32.ShellExecuteW
    shell_execute.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                              ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
    shell_execute.restype = ctypes.c_void_p  # HINSTANCE; valores > 32 indicam sucesso
    logger.info("Solicitando elevação UAC...")
    ret = shell_execute(None, "runas", executable, params, os.getcwd(), 1)  # SW_SHOWNORMAL
    if (ret or 0) > 32:
        return True
    logger.warning("Elevação UAC recusada ou falhou (código %s). Abrindo em modo limitado.", ret)
    return False


def _install_exception_hooks() -> None:
    """Garante que exceções não tratadas sejam registradas no log."""
    def _hook(exc_type, exc, tb):
        logger.critical("Exceção não tratada", exc_info=(exc_type, exc, tb))

    def _thread_hook(args):
        logger.critical("Exceção não tratada na thread %s", args.thread.name if args.thread else "?",
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = _hook
    threading.excepthook = _thread_hook


def main() -> int:
    """Inicializa a interface gráfica do aplicativo após validação de privilégios."""
    log_path = setup_logging()
    _install_exception_hooks()

    if sys.platform == "win32" and not is_admin() and NO_ELEVATE_FLAG not in sys.argv:
        if request_admin_elevation():
            return 0

    try:
        from gui import PCHealthApp
    except ImportError as err:
        logger.exception("Falha ao importar módulos")
        show_error("PC Health Check - Dependências ausentes",
                   f"Erro ao carregar módulos: {err}\n\nExecute: pip install -r requirements.txt")
        return 1

    try:
        app = PCHealthApp(is_elevated=is_admin(), log_path=log_path)
        app.mainloop()
    except Exception as err:
        logger.exception("Erro fatal na aplicação")
        show_error("PC Health Check - Erro fatal", f"{type(err).__name__}: {err}\n\nDetalhes em: {log_path}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
