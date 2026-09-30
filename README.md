# 🛠️ PC Health Check & Auto-Fix

Um aplicativo desktop profissional desenvolvido em Python para diagnóstico profundo e resolução automática de problemas em sistemas Windows 10 e 11. 

Este projeto automatiza rotinas de infraestrutura e suporte técnico, fornecendo uma interface gráfica moderna e integração direta com ferramentas nativas do sistema operacional (WMI, SFC, DISM, PowerShell e CMD).

## 🚀 Funcionalidades

O sistema opera em duas fases principais de automação:

### 🔍 Fase 1: Motor de Diagnóstico (Análise)
* **Monitoramento de Hardware:** Análise em tempo real de gargalos de CPU e Memória RAM.
* **Saúde do Armazenamento:** Verificação de espaço em disco, status S.M.A.R.T. (via WMI), acúmulo de arquivos temporários e necessidade de desfragmentação.
* **Conectividade:** Testes de latência (Ping) e perda de pacotes para o DNS do Google (8.8.8.8), além de listagem de adaptadores ativos.
* **Integridade do SO:** Verificação de violações no sistema via `sfc /verifyonly` e checagem de serviços críticos do Windows (Ex: Windows Update, Defender, Spooler).

### ⚡ Fase 2: Motor de Resolução (Auto-Fix)
* **Otimização de Espaço:** Limpeza automatizada e segura das pastas `%TEMP%`, `C:\Windows\Temp`, `Prefetch` e Lixeira.
* **Reparo de Rede:** Redefinição completa da pilha TCP/IP e DNS (`ipconfig /flushdns`, `release`, `renew`, `netsh winsock reset`).
* **Reparo de Integridade (OS):** Execução automatizada do `DISM /RestoreHealth` e `sfc /scannow`.
* **Gerenciamento de Processos:** Encerramento seguro de processos de usuário ofensores (protegendo processos críticos do sistema para evitar BSOD).

### 📄 Recursos Extras
* **Geração de Relatórios:** Exportação dos dados de diagnóstico e logs do terminal para arquivos `.txt`.
* **Console Integrado:** Terminal embutido na interface (CustomTkinter) com streaming de logs de execução em tempo real via multi-threading.
* **Elevação de Privilégios (UAC):** Detecção nativa de permissões, solicitando acesso de Administrador automaticamente via `ShellExecuteW`.

## 💻 Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Interface Gráfica (GUI):** CustomTkinter
* **Integrações de Sistema:** `psutil` (hardware/processos), `wmi` (Windows Management Instrumentation), `ctypes` e `subprocess`.
* **Distribuição:** PyInstaller (empacotamento `.exe` autônomo com manifesto de Administrador).

## ⚙️ Como Executar o Projeto

**1. Clone o repositório:**
```bash
git clone [https://github.com/GustavoCintra98/PC-Health-Check-AutoFix.git](https://github.com/GustavoCintra98/PC-Health-Check-AutoFix.git)
cd PC-Health-Check-AutoFix
```

**2. Instale as dependências:**
```bash
pip install -r requirements.txt
```

**3. Inicie a aplicação:**
Para garantir que todas as ferramentas de reparo do Windows funcionem corretamente, o aplicativo exige privilégios administrativos.
* **Recomendado:** Execute o arquivo `run_admin.bat` com o botão direito -> "Executar como Administrador".
* **Via Terminal:** Execute `python main.py` (o script solicitará a elevação UAC automaticamente).

## 📦 Como Compilar (.exe)

O repositório já inclui um script de automação para transformar o projeto em um executável portátil. Basta executar:

```bash
build_exe.bat
```
O arquivo final `PC_Health_Check_AutoFix.exe` será gerado na pasta `dist/`, pronto para rodar em qualquer máquina Windows x64 sem necessidade de instalar o Python.

## 📝 Licença

Este projeto está sob a licença MIT. Sinta-se à vontade para usá-lo e aprimorá-lo.
