import React from 'react';
import { 
  HardDrive, 
  Trash2, 
  FolderSync, 
  CheckCircle2, 
  AlertCircle, 
  ShieldAlert, 
  Sparkles,
  Layers,
  FileBox
} from 'lucide-react';
import { StorageCategory, DiskDrive } from '../types/system';

interface StorageTabProps {
  storageCategories: StorageCategory[];
  drives: DiskDrive[];
  isAdmin: boolean;
  onCleanCategory: (id: string) => void;
  onCleanAllStorage: () => void;
}

export const StorageTab: React.FC<StorageTabProps> = ({
  storageCategories,
  drives,
  isAdmin,
  onCleanCategory,
  onCleanAllStorage
}) => {
  const totalTrashSizeMb = storageCategories.reduce(
    (acc, curr) => !curr.isCleaned ? acc + curr.sizeMb : acc, 0
  );
  const totalFilesCount = storageCategories.reduce(
    (acc, curr) => !curr.isCleaned ? acc + curr.fileCount : acc, 0
  );

  return (
    <div className="space-y-6">
      {/* Overview & Quick Action */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <HardDrive className="h-5 w-5 text-indigo-400" />
              <span>Análise Profunda & Otimização de Armazenamento</span>
            </h2>
            <p className="mt-1 text-xs text-slate-300">
              Varredura de lixo acumulado no Windows: <code className="text-cyan-400">%TEMP%</code>, <code className="text-cyan-400">Prefetch</code>, <code className="text-cyan-400">Lixeira</code> e integridade física S.M.A.R.T.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onCleanAllStorage}
              disabled={totalTrashSizeMb === 0}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-950 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="h-4 w-4" />
              <span>Limpar Todos os Temporários ({(totalTrashSizeMb / 1024).toFixed(1)} GB)</span>
            </button>
          </div>
        </div>

        {/* Disk Partitions Summary */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {drives.map((drive) => (
            <div key={drive.letter} className="rounded-lg bg-slate-950/60 border border-slate-800 p-4">
              <div className="flex items-center justify-between text-xs mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white font-mono text-sm">{drive.letter}</span>
                  <span className="text-slate-400">[{drive.label}]</span>
                  <span className="text-[10px] rounded bg-slate-800 px-1.5 py-0.5 text-slate-300">
                    {drive.isSSD ? 'NVMe SSD' : 'HDD'}
                  </span>
                </div>
                <span className="font-mono text-slate-300">
                  {drive.freeGb} GB livres de {drive.totalGb} GB
                </span>
              </div>

              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${drive.usedPercent > 90 ? 'bg-rose-500' : drive.usedPercent > 75 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                  style={{ width: `${drive.usedPercent}%` }}
                />
              </div>

              <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  <span>S.M.A.R.T.: <strong>{drive.smartStatus}</strong> (0 Setores Defeituosos)</span>
                </span>
                <span>Fragmentação: <strong>{drive.fragmentationPercent}%</strong> ({drive.isSSD ? 'TRIM Otimizado' : 'Desfrag OK'})</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Junk Breakdown Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
          <FolderSync className="h-4 w-4 text-cyan-400" />
          <span>Detecção de Arquivos Temporários e Cache (%TEMP% & Prefetch)</span>
        </h3>

        <div className="grid grid-cols-1 gap-3">
          {storageCategories.map((cat) => (
            <div 
              key={cat.id} 
              className={`rounded-xl border p-4 transition-all ${
                cat.isCleaned 
                  ? 'border-emerald-500/20 bg-emerald-950/10' 
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <FileBox className="h-4 w-4 text-slate-400" />
                    <span className="text-sm font-semibold text-white">{cat.name}</span>
                    {cat.requiresAdmin && (
                      <span className="text-[10px] text-amber-400 rounded bg-amber-950/40 border border-amber-500/30 px-1.5 py-0.5">
                        Requer Admin
                      </span>
                    )}
                  </div>
                  <div className="text-xs font-mono text-slate-400">{cat.path}</div>
                  <div className="text-xs text-slate-400">{cat.description}</div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <div className="text-right">
                    {cat.isCleaned ? (
                      <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Limpo com Sucesso</span>
                      </div>
                    ) : (
                      <>
                        <div className="text-sm font-mono font-bold text-slate-200">
                          {cat.sizeMb > 1024 
                            ? `${(cat.sizeMb / 1024).toFixed(2)} GB` 
                            : `${cat.sizeMb.toFixed(1)} MB`}
                        </div>
                        <div className="text-[11px] text-slate-500 font-mono">
                          {cat.fileCount.toLocaleString()} arquivos
                        </div>
                      </>
                    )}
                  </div>

                  {!cat.isCleaned && (
                    <button
                      onClick={() => onCleanCategory(cat.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-slate-400" />
                      <span>Limpar</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Safety & Robust Error Handling Notice */}
      <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-400 space-y-1">
        <div className="font-semibold text-slate-300 flex items-center gap-2">
          <ShieldAlert className="h-4 w-4 text-cyan-400" />
          <span>Garantia de Segurança e Tolerância a Falhas (Try/Except)</span>
        </div>
        <p>
          O algoritmo de limpeza varre o diretório com <code className="text-slate-300">os.walk()</code> e remove arquivos individualmente.
          Se um arquivo temporário estiver atualmente bloqueado em uso por um processo ativo do Windows, ele dispara <code className="text-slate-300">PermissionError</code> ou <code className="text-slate-300">OSError</code> e é ignorado silenciosamente, garantindo que o aplicativo nunca feche inesperadamente nem cause instabilidade no sistema operacional.
        </p>
      </div>
    </div>
  );
};
