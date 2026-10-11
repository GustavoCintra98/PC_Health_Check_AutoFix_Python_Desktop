// Os arquivos são importados diretamente da raiz do repositório (`?raw` do Vite),
// então o demo sempre exibe e baixa o código real do aplicativo desktop — sem cópias
// que possam ficar desatualizadas.
import mainPy from '../../main.py?raw';
import diagnosticsPy from '../../diagnostics.py?raw';
import fixerPy from '../../fixer.py?raw';
import guiPy from '../../gui.py?raw';
import reportPy from '../../report.py?raw';
import utilsPy from '../../utils.py?raw';
import requirementsTxt from '../../requirements.txt?raw';
import requirementsDevTxt from '../../requirements-dev.txt?raw';
import pyprojectToml from '../../pyproject.toml?raw';
import specFile from '../../PC_Health_Check_AutoFix.spec?raw';
import runAdminBat from '../../run_admin.bat?raw';
import buildExeBat from '../../build_exe.bat?raw';
import readmeMd from '../../README.md?raw';
import testParsersPy from '../../tests/test_parsers.py?raw';
import testUtilsPy from '../../tests/test_utils.py?raw';
import testFixerPy from '../../tests/test_fixer.py?raw';

export interface PythonFileItem {
  id: string;
  filename: string;
  language: string;
  description: string;
  category: 'core' | 'engine' | 'gui' | 'config' | 'scripts' | 'tests';
  code: string;
}

export const PYTHON_PROJECT_FILES: PythonFileItem[] = [
  {
    id: 'main',
    filename: 'main.py',
    language: 'python',
    description: 'Ponto de entrada: elevação UAC (com modo limitado se recusada), log em arquivo e erros fatais',
    category: 'core',
    code: mainPy,
  },
  {
    id: 'diagnostics',
    filename: 'diagnostics.py',
    language: 'python',
    description: 'Fase 1: diagnóstico de CPU, RAM, discos (WMI), rede, imagem do Windows e serviços — sem valores inventados',
    category: 'engine',
    code: diagnosticsPy,
  },
  {
    id: 'fixer',
    filename: 'fixer.py',
    language: 'python',
    description: 'Fase 2: correções verificadas por etapa (restauração, limpeza segura, rede escalonada, DISM/SFC, winget)',
    category: 'engine',
    code: fixerPy,
  },
  {
    id: 'gui',
    filename: 'gui.py',
    language: 'python',
    description: 'Interface CustomTkinter com fila thread-safe, progresso por etapa, cancelamento e confirmação',
    category: 'gui',
    code: guiPy,
  },
  {
    id: 'utils',
    filename: 'utils.py',
    language: 'python',
    description: 'Comandos com encoding correto (OEM/UTF-16), PowerShell, varredura segura de arquivos, COM/WMI e log',
    category: 'core',
    code: utilsPy,
  },
  {
    id: 'report',
    filename: 'report.py',
    language: 'python',
    description: 'Geração do relatório em texto (diagnóstico, correções aplicadas e log)',
    category: 'core',
    code: reportPy,
  },
  {
    id: 'requirements',
    filename: 'requirements.txt',
    language: 'plaintext',
    description: 'Dependências de execução',
    category: 'config',
    code: requirementsTxt,
  },
  {
    id: 'requirements_dev',
    filename: 'requirements-dev.txt',
    language: 'plaintext',
    description: 'Dependências de desenvolvimento, testes e empacotamento',
    category: 'config',
    code: requirementsDevTxt,
  },
  {
    id: 'pyproject',
    filename: 'pyproject.toml',
    language: 'toml',
    description: 'Configuração do pytest e do ruff',
    category: 'config',
    code: pyprojectToml,
  },
  {
    id: 'spec',
    filename: 'PC_Health_Check_AutoFix.spec',
    language: 'python',
    description: 'Configuração do PyInstaller (manifesto de Administrador, assets do CustomTkinter)',
    category: 'config',
    code: specFile,
  },
  {
    id: 'run_admin',
    filename: 'run_admin.bat',
    language: 'bat',
    description: 'Executa o app com elevação de Administrador e instala as dependências',
    category: 'scripts',
    code: runAdminBat,
  },
  {
    id: 'build_exe',
    filename: 'build_exe.bat',
    language: 'bat',
    description: 'Instala dependências, roda os testes e compila o .exe pelo .spec',
    category: 'scripts',
    code: buildExeBat,
  },
  {
    id: 'test_parsers',
    filename: 'tests/test_parsers.py',
    language: 'python',
    description: 'Testes dos parsers de saída do Windows (pt-BR e en-US)',
    category: 'tests',
    code: testParsersPy,
  },
  {
    id: 'test_utils',
    filename: 'tests/test_utils.py',
    language: 'python',
    description: 'Testes da limpeza segura (junctions, idade mínima, somente-leitura) e da execução de comandos',
    category: 'tests',
    code: testUtilsPy,
  },
  {
    id: 'test_fixer',
    filename: 'tests/test_fixer.py',
    language: 'python',
    description: 'Testes do fluxo do Auto-Fix (cancelamento, confirmação, etapas Admin, PID reutilizado)',
    category: 'tests',
    code: testFixerPy,
  },
  {
    id: 'readme',
    filename: 'README.md',
    language: 'markdown',
    description: 'Instalação, arquitetura, desenvolvimento e compilação',
    category: 'config',
    code: readmeMd,
  },
];

/**
 * Conteúdo pronto para salvar em disco. Arquivos .bat precisam de quebras de linha
 * CRLF: com LF puro o cmd.exe pode interpretar errado rótulos e `goto`.
 */
export function fileContentForDownload(file: PythonFileItem): string {
  return file.filename.endsWith('.bat') ? file.code.replace(/\r?\n/g, '\r\n') : file.code;
}
