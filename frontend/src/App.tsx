import { useState } from 'react'
import DiffAnalyzer from './pages/DiffAnalyzer'
import ManualIntake from './pages/ManualIntake'
import SIAViewer from './pages/SIAViewer'

type Page = 'diff' | 'manual' | 'sia'

export default function App() {
  const [page, setPage] = useState<Page>('diff')
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [siaId, setSiaId] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-slate-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛡️</span>
            <div>
              <h1 className="text-lg font-bold tracking-tight">cATO Advisor</h1>
              <p className="text-xs text-slate-400">ATO Artifact Impact Detection · Prototype v0.1</p>
            </div>
          </div>
          <nav className="flex gap-1">
            {([
              ['diff',   '🔍 Diff Analyzer',  'UC1'],
              ['manual', '📋 Manual Intake',   'UC2'],
              ['sia',    '📄 SIA Generator',   'UC3'],
            ] as [Page, string, string][]).map(([id, label, tag]) => (
              <button key={id} onClick={() => setPage(id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                  page === id ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                }`}>
                {label}
                <span className="text-xs opacity-60 font-mono">{tag}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-6 py-8">
        {page === 'diff'   && <DiffAnalyzer onAnalysisComplete={(id) => { setAnalysisId(id); setPage('sia') }} />}
        {page === 'manual' && <ManualIntake onChangeSubmitted={(id) => { setAnalysisId(id); setPage('sia') }} />}
        {page === 'sia'    && <SIAViewer analysisId={analysisId} siaId={siaId} onSiaGenerated={setSiaId} />}
      </main>
    </div>
  )
}
