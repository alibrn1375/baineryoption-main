import React, { useState } from 'react';
import { pythonFiles } from '../data/pythonCodeExports';
import { Check, Code, Copy, Download, FileCode, Terminal, X } from 'lucide-react';

interface PythonExportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PythonExportModal: React.FC<PythonExportModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [selectedFileIdx, setSelectedFileIdx] = useState(0);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const currentFile = pythonFiles[selectedFileIdx];

  const handleCopy = () => {
    navigator.clipboard.writeText(currentFile.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([currentFile.code], { type: 'text/x-python;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = currentFile.filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <Code className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                کدهای پایتون موتور تحقیقاتی FO-X 5M
                <span className="text-[11px] font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                  Python 3.11+ / Pydantic / Numba
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                فایل‌های منبع اصلی برای اجرای محلی، بک‌تستینگ و پردازش تیک‌های بورس CME
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body Layout */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-4 overflow-hidden">
          
          {/* Left Sidebar: File List */}
          <div className="md:col-span-1 border-b md:border-b-0 md:border-l border-slate-800 bg-slate-950/60 p-3 space-y-2 overflow-y-auto">
            <span className="text-[11px] font-mono text-slate-500 font-bold px-2 block mb-2">
              ماژول‌های پروژه:
            </span>
            {pythonFiles.map((file, idx) => (
              <button
                key={file.filename}
                onClick={() => setSelectedFileIdx(idx)}
                className={`w-full text-right p-2.5 rounded-lg text-xs font-mono transition-all flex items-center gap-2 ${
                  selectedFileIdx === idx
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <FileCode className="w-4 h-4 shrink-0 text-amber-400" />
                <div className="truncate">
                  <div className="truncate">{file.filename}</div>
                  <div className="text-[10px] text-slate-500 truncate">{file.category}</div>
                </div>
              </button>
            ))}

            <div className="mt-4 p-3 rounded-lg bg-slate-900 border border-slate-800 text-[11px] text-slate-400">
              <div className="flex items-center gap-1 text-amber-400 font-bold mb-1">
                <Terminal className="w-3 h-3" />
                <span>نحوه اجرا در محیط محلی:</span>
              </div>
              <code className="text-[10px] font-mono text-slate-300 block bg-slate-950 p-1.5 rounded mt-1">
                pip install pydantic polars numba pytest duckdb
              </code>
            </div>
          </div>

          {/* Right Editor Area */}
          <div className="md:col-span-3 flex flex-col bg-slate-900 overflow-hidden">
            
            {/* Editor Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-mono text-amber-400 font-bold">{currentFile.filename}</span>
                <span className="text-slate-500 text-[11px]">— {currentFile.description}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs flex items-center gap-1 transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'کپی شد' : 'کپی کد'}</span>
                </button>

                <button
                  onClick={handleDownload}
                  className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold text-xs flex items-center gap-1 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>دانلود .py</span>
                </button>
              </div>
            </div>

            {/* Code Content */}
            <div className="flex-1 p-4 overflow-auto bg-slate-950 font-mono text-xs text-slate-200 leading-relaxed">
              <pre>
                <code>{currentFile.code}</code>
              </pre>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};
