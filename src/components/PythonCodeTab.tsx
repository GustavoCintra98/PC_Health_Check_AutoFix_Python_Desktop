import React, { useState } from 'react';
import { 
  FileCode, 
  Copy, 
  Check, 
  Download, 
  Archive, 
  Terminal, 
  FolderDown, 
  ExternalLink,
  Shield,
  Layers,
  Sparkles
} from 'lucide-react';
import JSZip from 'jszip';
import { PYTHON_PROJECT_FILES, PythonFileItem } from '../data/pythonSourceCode';

export const PythonCodeTab: React.FC = () => {
  const [selectedFileId, setSelectedFileId] = useState<string>('main');
  const [copied, setCopied] = useState<boolean>(false);
  const [isZipping, setIsZipping] = useState<boolean>(false);

  const currentFile = PYTHON_PROJECT_FILES.find(f => f.id === selectedFileId) || PYTHON_PROJECT_FILES[0];

  const handleCopyCode = () => {
    navigator.clipboard.writeText(currentFile.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSingleFile = () => {
    const blob = new Blob([currentFile.code], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = currentFile.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleDownloadFullZip = async () => {
    try {
      setIsZipping(true);
      const zip = new JSZip();
      
      // Add all project files to zip
      PYTHON_PROJECT_FILES.forEach(item => {
        zip.file(item.filename, item.code);
      });

      const zipBlob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(zipBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'PC_Health_Check_AutoFix_Python_Desktop.zip';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Falha ao gerar arquivo ZIP:', err);
    } finally {
      setIsZipping(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Code Header & Zip Download Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FileCode className="h-5 w-5 text-cyan-400" />
              <span>Código-Fonte Completo do Aplicativo Desktop (Python & CustomTkinter)</span>
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Arquitetura modular pronta para produção no Windows 10/11: verificação UAC nativa via <code className="text-cyan-400">ctypes</code>, <code className="text-cyan-400">psutil</code>, <code className="text-cyan-400">wmi</code> e <code className="text-cyan-400">PowerShell</code>.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleCopyCode}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4 text-slate-400" />}
              <span>{copied ? 'Código Copiado!' : 'Copiar Arquivo Atual'}</span>
            </button>

            <button
              onClick={handleDownloadSingleFile}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              <Download className="h-4 w-4 text-slate-400" />
              <span>Baixar {currentFile.filename}</span>
            </button>

            <button
              onClick={handleDownloadFullZip}
              disabled={isZipping}
              className="flex items-center gap-2 px-5 py-2 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-500 rounded-lg shadow-md shadow-cyan-950 transition-colors disabled:opacity-50"
            >
              <Archive className="h-4 w-4" />
              <span>{isZipping ? 'Compactando...' : 'Baixar Projeto Completo (.ZIP)'}</span>
            </button>
          </div>
        </div>

        {/* Quick run command guide */}
        <div className="mt-4 rounded-lg bg-slate-950/80 border border-slate-800 p-3 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2 font-mono text-slate-300">
            <Terminal className="h-4 w-4 text-cyan-400 shrink-0" />
            <span>Passo 1: Instale as bibliotecas</span>
            <span className="rounded bg-slate-900 border border-slate-700 px-2 py-0.5 text-cyan-300">
              pip install customtkinter psutil wmi pywin32
            </span>
          </div>

          <div className="flex items-center gap-2 font-mono text-slate-300">
            <span>Passo 2: Execute com UAC</span>
            <span className="rounded bg-slate-900 border border-slate-700 px-2 py-0.5 text-emerald-300">
              python main.py
            </span>
          </div>
        </div>
      </div>

      {/* Code Viewer Container */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-2xl">
        {/* File Tabs Navigation */}
        <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-800 bg-slate-900/90 px-3 pt-2">
          {PYTHON_PROJECT_FILES.map((file) => {
            const isSelected = file.id === selectedFileId;
            return (
              <button
                key={file.id}
                onClick={() => setSelectedFileId(file.id)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono rounded-t-lg transition-colors whitespace-nowrap border-t border-x ${
                  isSelected 
                    ? 'bg-slate-950 border-slate-700 text-cyan-400 font-semibold' 
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <FileCode className="h-3.5 w-3.5" />
                <span>{file.filename}</span>
              </button>
            );
          })}
        </div>

        {/* File Description Bar */}
        <div className="flex items-center justify-between border-b border-slate-800/60 bg-slate-900/40 px-4 py-2 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-200">{currentFile.filename}</span>
            <span>—</span>
            <span>{currentFile.description}</span>
          </div>
          <div className="font-mono text-[11px] text-slate-500">
            {currentFile.code.split('\n').length} linhas · UTF-8
          </div>
        </div>

        {/* Syntax Code Display */}
        <div className="relative p-4 font-mono text-xs text-slate-200 overflow-x-auto max-h-[580px] overflow-y-auto leading-relaxed select-text bg-slate-950">
          <pre className="tab-size-4">
            <code>{currentFile.code}</code>
          </pre>
        </div>
      </div>

      {/* Technical Architecture Notes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Shield className="h-4 w-4 text-emerald-400" />
            <span>Elevação UAC Transparente</span>
          </h4>
          <p className="text-xs text-slate-400">
            O <code className="text-slate-300">main.py</code> consulta <code className="text-slate-300">ctypes.windll.shell32.IsUserAnAdmin()</code>. Se não estiver elevado, reinvoca o executável via verbo <code className="text-cyan-400">'runas'</code> sem abrir janelas de console duplicadas.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="h-4 w-4 text-cyan-400" />
            <span>Execução Não-Bloqueante (Threads)</span>
          </h4>
          <p className="text-xs text-slate-400">
            A interface <code className="text-slate-300">CustomTkinter</code> roda em loop principal enquanto o diagnóstico e os reparos executam em <code className="text-slate-300">threading.Thread(daemon=True)</code>, mantendo a GUI 100% fluida durante chamadas demoradas de SFC ou DISM.
          </p>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 space-y-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span>Compilação Standalone (.exe)</span>
          </h4>
          <p className="text-xs text-slate-400">
            Com o script <code className="text-slate-300">build_exe.bat</code> fornecido, é gerado um arquivo <code className="text-slate-300">PC_Health_Check_AutoFix.exe</code> único com manifesto de Administrador embutido (<code className="text-purple-300">--uac-admin</code>) via PyInstaller.
          </p>
        </div>
      </div>
    </div>
  );
};
