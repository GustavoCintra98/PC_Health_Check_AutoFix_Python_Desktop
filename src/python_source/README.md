# PC Health Check & Auto-Fix 🚀
**Aplicativo Desktop Profissional de Diagnóstico Profundo e Resolução Automática para Windows**

Desenvolvido para engenheiros de infraestrutura, técnicos de suporte e administradores de sistemas Windows 10/11.

---

## 🛠️ Arquitetura Modular

| Módulo | Responsabilidade |
| :--- | :--- |
| `main.py` | Ponto de entrada, checagem de privilégios e elevação UAC transparente via `ShellExecuteW`. |
| `diagnostics.py` | **Fase 1:** Motor de análise de CPU, RAM, processos consumidores, discos, SMART, fragmentação, rede (ping 8.8.8.8) e integridade SFC/serviços. |
| `fixer.py` | **Fase 2:** Motor de reparo automático (limpeza de `%TEMP%` e Prefetch, esvaziamento de Lixeira, execução de SFC/DISM, reset de DNS e catálogo Winsock, encerramento de processos ofensores). |
| `gui.py` | Interface gráfica moderna construída com `CustomTkinter`, console de streaming de comandos em tempo real e threads assíncronas. |
| `run_admin.bat` | Inicializador em lote para execução direta com elevação de Administrador. |
| `build_exe.bat` | Script automatizado para empacotar em um executável autônomo único com `PyInstaller` e manifesto UAC. |

---

## 📦 Instalação das Dependências

Abra o prompt de comando (CMD ou PowerShell) e execute:

```bash
pip install -r requirements.txt
```

Ou instale manualmente as bibliotecas necessárias:
```bash
pip install customtkinter psutil wmi pywin32 packaging
```

> **Nota:** Em sistemas Windows de 64 bits, certifique-se de executar com privilégios de Administrador para que a limpeza de `C:\Windows\Prefetch`, o reparo SFC/DISM e o comando `netsh winsock reset` funcionem sem restrições do sistema.

---

## 🚀 Como Executar

### Opção 1: Via Inicializador Batch (Recomendado)
Clique com o botão direito em `run_admin.bat` e selecione **"Executar como Administrador"**.

### Opção 2: Via Terminal Python
```bash
python main.py
```
*(Caso não esteja como Administrador, o próprio script abrirá a janela do UAC para autorizar a elevação).*

---

## ⚙️ Como Gerar o Executável (.exe)

Para criar um arquivo executável único sem necessidade de ter Python instalado na máquina do usuário final:

```bash
run build_exe.bat
```
Ou manualmente:
```bash
pyinstaller --noconsole --onefile --uac-admin --name="PC_Health_Check_AutoFix" main.py
```
O executável final estará disponível no diretório `dist/PC_Health_Check_AutoFix.exe`.
