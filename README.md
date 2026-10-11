# 🛠️ PC Health Check & Auto-Fix

Aplicativo desktop em Python para diagnóstico profundo e resolução automática de problemas em Windows 10 e 11.

Automatiza rotinas de infraestrutura e suporte técnico com uma interface gráfica moderna e integração direta com ferramentas nativas do sistema (WMI, SFC, DISM, PowerShell e CMD).

**Princípio de projeto:** nenhum valor é inventado e nenhuma ação é reportada como sucesso sem verificação. O que não pode ser medido aparece como **N/D**.

## 🚀 Funcionalidades

### 🔍 Fase 1: Diagnóstico
* **CPU e RAM:** uso total e por processo (amostragem real de 1s), com identificação dos processos que de fato causam gargalo.
* **Armazenamento:** espaço livre, saúde física dos discos via WMI (`MSFT_PhysicalDisk` e predição de falha S.M.A.R.T.), tipo de mídia (SSD/HDD), fragmentação (apenas em HDD) e temporários elegíveis para limpeza.
* **Rede:** latência e perda de pacotes via ping para 8.8.8.8, com fallback TCP quando o ICMP está bloqueado, além de teste de resolução DNS.
* **Sistema:** saúde da imagem do Windows (`Repair-WindowsImage -CheckHealth`), `sfc /verifyonly` opcional e serviços essenciais. Serviços manuais parados (ex.: Windows Update ocioso) não são tratados como problema, e o Defender é ignorado quando há outro antivírus.

### ⚡ Fase 2: Auto-Fix (com confirmação)
Antes de executar, o app mostra o que será feito e os impactos de cada ação.
* **Ponto de restauração:** criado e verificado antes de qualquer alteração. Se falhar, o usuário decide se continua.
* **Temporários:** remove arquivos com mais de 24h de `%TEMP%` e `C:\Windows\Temp`, sem atravessar junctions ou symlinks.
* **Lixeira:** opcional e desmarcada por padrão.
* **Rede (escalonado):** limpa o cache DNS. Só renova o IP se não houver conexão e só redefine Winsock/TCP-IP se a conexão continuar sem voltar (nesse caso é preciso reiniciar).
* **Windows:** `DISM /RestoreHealth` (apenas se a imagem não estiver saudável) + `sfc /scannow`, e início de serviços essenciais parados, com verificação do estado final.
* **Processos:** encerra apenas os que causam gargalo, confirmando que o PID não foi reutilizado. Processos do sistema e o próprio app são protegidos.
* **Windows Update:** limpeza do cache de downloads, aguardando os serviços pararem de fato.
* **Winget:** atualização de aplicativos com saída em tempo real e timeout.

### 📄 Recursos extras
* Barra de progresso por etapa, tempo decorrido e botão **Cancelar** (interrompe entre etapas).
* Relatório `.txt` com diagnóstico, correções aplicadas e log.
* Log persistente em `%LOCALAPPDATA%\PCHealthCheck\logs\app.log`.
* Sem privilégios de Administrador, o app abre em modo limitado e desativa as opções que exigem elevação.

## 🧱 Arquitetura

| Módulo | Responsabilidade |
| :--- | :--- |
| `main.py` | Ponto de entrada, elevação UAC, log e tratamento de erros fatais. |
| `diagnostics.py` | Fase 1: motor de análise e parsers puros (testáveis) das saídas do Windows. |
| `fixer.py` | Fase 2: motor de correção, plano de ações e relatório por etapa (`StepResult`). |
| `gui.py` | Interface CustomTkinter. As threads de trabalho se comunicam com a UI por fila. |
| `report.py` | Geração do relatório em texto. |
| `utils.py` | Execução de comandos com encoding correto (OEM/UTF-16), PowerShell, varredura segura de arquivos, COM/WMI e log. |
| `tests/` | Testes `pytest` (parsers pt-BR/en-US, segurança da limpeza, fluxo do Auto-Fix). |

## ⚙️ Como executar

**1. Clone o repositório:**
```bash
git clone https://github.com/GustavoCintra98/PC-Health-Check-AutoFix.git
cd PC-Health-Check-AutoFix
```

**2. Instale as dependências (Python 3.9+):**
```bash
pip install -r requirements.txt
```

**3. Inicie a aplicação:**
* **Recomendado:** execute `run_admin.bat`. Ele pede elevação, instala as dependências e inicia o app.
* **Via terminal:** `python main.py`. O app solicita elevação UAC; se for recusada, abre em modo limitado.

## 🧪 Desenvolvimento

```bash
pip install -r requirements-dev.txt
pytest          # testes
ruff check .    # lint
```

## 📦 Como compilar (.exe)

```bash
build_exe.bat
```
O script instala as dependências de build, roda os testes e compila usando `PC_Health_Check_AutoFix.spec`. O executável é gerado em `dist\PC_Health_Check_AutoFix.exe` e já solicita Administrador ao abrir.

## 📝 Licença

Este projeto está sob a licença MIT.
