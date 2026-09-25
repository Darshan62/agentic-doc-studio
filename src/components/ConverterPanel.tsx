import React, { useState } from 'react';
import { RefreshCw, FileText, Presentation, ArrowRight, Download, CheckCircle2 } from 'lucide-react';

import { postJson, errorMessage } from '../api';

export const ConverterPanel: React.FC = () => {
  const [direction, setDirection] = useState<'docx_to_pptx' | 'pptx_to_docx'>('docx_to_pptx');
  const [isConverting, setIsConverting] = useState(false);
  const [convertedArtifact, setConvertedArtifact] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleConvert = async () => {
    setIsConverting(true);
    setConvertedArtifact(null);
    setError(null);
    try {
      const data = await postJson<{ artifact: string }>('/api/convert', { direction });
      setConvertedArtifact(data.artifact);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <RefreshCw className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Bidirectional Format Converter
            </h2>
          </div>
          <span className="text-xs bg-indigo-500/20 text-indigo-300 px-2.5 py-1 rounded-full border border-indigo-500/30">
            ECMA-376 OpenXML Engine
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Transform Word proposals (.docx) into 16:9 presentation slide decks (.pptx) or slide decks into narrative Word reports without losing structure.
        </p>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6 max-w-2xl mx-auto text-center">
        {/* Direction Switcher */}
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => setDirection('docx_to_pptx')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              direction === 'docx_to_pptx'
                ? 'border-blue-500 bg-blue-950/40 shadow-lg shadow-blue-500/20 ring-1 ring-blue-500'
                : 'border-slate-800 bg-slate-800/40 hover:bg-slate-800'
            }`}
          >
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-5 h-5 text-blue-400" />
              <ArrowRight className="w-4 h-4 text-slate-500" />
              <Presentation className="w-5 h-5 text-amber-400" />
            </div>
            <h4 className="text-sm font-bold text-white">DOCX to PPTX</h4>
            <p className="text-xs text-slate-400 mt-1">Converts Word chapters, tables, and bullets into 16:9 widescreen slides</p>
          </button>

          <button
            onClick={() => setDirection('pptx_to_docx')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              direction === 'pptx_to_docx'
                ? 'border-indigo-500 bg-indigo-950/40 shadow-lg shadow-indigo-500/20 ring-1 ring-indigo-500'
                : 'border-slate-800 bg-slate-800/40 hover:bg-slate-800'
            }`}
          >
            <div className="flex items-center space-x-2 mb-2">
              <Presentation className="w-5 h-5 text-amber-400" />
              <ArrowRight className="w-4 h-4 text-slate-500" />
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <h4 className="text-sm font-bold text-white">PPTX to DOCX</h4>
            <p className="text-xs text-slate-400 mt-1">Compiles slide cards, metrics, and diagrams into a structured narrative report</p>
          </button>
        </div>

        {/* Action Button */}
        <button
          onClick={handleConvert}
          disabled={isConverting}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold py-3 px-6 rounded-xl transition-all shadow-lg hover:shadow-indigo-500/20 disabled:opacity-50 cursor-pointer flex items-center justify-center space-x-2 text-sm"
        >
          {isConverting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
              <span>Executing OpenXML Bidirectional Translation...</span>
            </>
          ) : (
            <span>Run {direction === 'docx_to_pptx' ? 'DOCX → PPTX' : 'PPTX → DOCX'} Conversion</span>
          )}
        </button>

        {error && <p role="alert" className="text-xs text-red-300">{error}</p>}

        {/* Conversion Result */}
        {convertedArtifact && (
          <div className="bg-emerald-950/30 border border-emerald-500/50 rounded-xl p-4 text-left space-y-2">
            <div className="flex items-center space-x-2 text-emerald-400 text-xs font-bold">
              <CheckCircle2 className="w-4 h-4" />
              <span>Conversion Successfully Completed!</span>
            </div>
            <p className="text-xs text-slate-300">
              Generated new artifact at: <span className="font-mono text-cyan-300">{convertedArtifact}</span>
            </p>
            <a
              href={`/api/download/converted?file=${encodeURIComponent(convertedArtifact)}`}
              download
              className="inline-flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition-colors shadow mt-2"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Converted File</span>
            </a>
          </div>
        )}
      </div>
    </div>
  );
};
