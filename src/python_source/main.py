"""
PC Health Check & Auto-Fix - Entry Point & UAC Privilege Elevation.

Este módulo é o ponto de entrada principal do aplicativo desktop.
Ele verifica se o processo atual possui privilégios de Administrador
no Windows (necessário para reparos do SFC, DISM, Winsock e limpeza do Prefetch).
Caso não possua, solicita elevação UAC automaticamente via ShellExecuteW.

Autor: Senior Infrastructure & Windows Automation Engineer
Licença: MIT
"""

import sys
import os
import ctypes

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


def request_admin_elevation() -> None:
    """
    Solicita elevação de privilégios via Prompt UAC do Windows e reinicia o script.
    Se o usuário aceitar no prompt UAC, o processo atual é encerrado e a nova
    instância elevada assume a execução.
    """
    if not is_admin():
        print("[!] Privilégios de Administrador não detectados. Solicitando elevação UAC...")
        try:
            # Reinvoca o interpretador Python com parâmetros completos via verbo 'runas'
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                params,
                None,
                1  # SW_SHOWNORMAL
            )
            # Se ret > 32 a chamada foi bem sucedida
            if ret > 32:
                sys.exit(0)
            else:
                print(f"[-] O usuário recusou a elevação UAC (Código de retorno: {ret}).")
        except Exception as e:
            print(f"[-] Falha ao solicitar privilégios administrativos: {e}")


def main():
    """Inicializa a interface gráfica do aplicativo após validação de privilégios."""
    # Solicita elevação de Administrador se estiver no Windows
    if sys.platform == "win32" and not is_admin():
        request_admin_elevation()
        return

    # Importa a GUI após validação de UAC
    try:
        from gui import PCHealthApp
        app = PCHealthApp(is_elevated=is_admin())
        app.mainloop()
    except ImportError as err:
        print(f"[-] Erro ao carregar módulos: {err}")
        print("[*] Certifique-se de executar: pip install -r requirements.txt")
        input("Pressione Enter para sair...")
    except Exception as err:
        print(f"[-] Erro fatal na aplicação: {err}")
        input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
