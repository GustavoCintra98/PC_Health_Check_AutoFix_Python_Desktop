import React from 'react';
import { Shield, ShieldAlert, Check, X, AlertTriangle } from 'lucide-react';

interface UACPromptModalProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isAdmin: boolean;
}

export const UACPromptModal: React.FC<UACPromptModalProps> = ({
  isOpen,
  onConfirm,
  onCancel,
  isAdmin
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      {/* Windows 11 Fluent UAC Elevation Modal Simulation */}
      <div className="w-full max-w-md overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Blue UAC Header bar */}
        <div className="bg-gradient-to-r from-blue-700 to-indigo-800 px-6 py-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-white/10 flex items-center justify-center border border-white/20">
            <Shield className="h-6 w-6 text-yellow-300" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Controle de Conta de Usuário (UAC)</h3>
            <p className="text-xs text-blue-200">Prompt de Elevação de Privilégios do Windows</p>
          </div>
        </div>

        {/* Content body */}
        <div className="p-6 space-y-4">
          <p className="text-sm font-medium text-slate-200">
            Deseja permitir que este aplicativo faça alterações no seu dispositivo?
          </p>

          <div className="rounded-lg bg-slate-950/60 p-4 border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Nome do Aplicativo:</span>
              <span className="font-semibold text-slate-200">PC Health Check & Auto-Fix</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Fornecedor:</span>
              <span className="font-semibold text-cyan-400">Engenharia de Sistemas Windows</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Executável:</span>
              <span className="font-mono text-slate-300">python.exe (via ShellExecuteW 'runas')</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Origem do Arquivo:</span>
              <span className="font-mono text-slate-400">Disco rígido local neste computador</span>
            </div>
          </div>

          <div className="flex items-start gap-2.5 rounded-md bg-amber-500/10 border border-amber-500/20 p-3 text-xs text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
            <p>
              Necessário para executar <strong>sfc /scannow</strong>, <strong>DISM</strong>, limpeza do diretório <strong>Prefetch</strong> e redefinição de catálogo de rede <strong>Winsock</strong>.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={onCancel}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              <span>Não (Executar como Usuário Comum)</span>
            </button>
            <button
              onClick={onConfirm}
              className="flex items-center gap-1.5 px-5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow-md shadow-blue-900/50 transition-colors"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Sim (Elevar como Administrador)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
