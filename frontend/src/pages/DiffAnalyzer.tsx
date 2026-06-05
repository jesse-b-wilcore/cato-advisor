import { useState } from 'react'
import ImpactReport from '../components/ImpactReport'

interface Props {
  onAnalysisComplete: (analysisId: string) => void
}

const TIER_STYLES: Record<string, string> = {
  green:  'bg-green-100  text-green-800  border-green-300',
  yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  orange: 'bg-orange-100 text-orange-800 border-orange-300',
  red:    'bg-red-100    text-red-800    border-red-300',
}

export default function DiffAnalyzer({ onAnalysisComplete }: Props) {
  const [mode, setMode] = useState<'paste' | 'url'>('paste')
  const [diffText, setDiffText] = useState('')
  const [prUrl, setPrUrl] = useState('')
  const [systemName, setSystemName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)

  const analyze = async () => {
    setError(null)
    setLoading(true)
    setResult(null)

    try {
      let res: Response
      if (mode === 'paste') {
        if (!diffText.trim()) { setError('Please paste a git diff before analyzing.'); setLoading(false); return }
        res = await fetch('/api/analysis/diff', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ diff_text: diffText, system_name: systemName || '[System Name]' }),
        })
      } else {
        if (!prUrl.trim()) { setError('Please enter a GitHub PR URL.'); setLoading(false); return }
        res = await fetch('/api/analysis/pr-url', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pr_url: prUrl, system_name: systemName || '[System Name]' }),
        })
      }

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }

      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setError(e.message || 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">PR Diff Analyzer</h2>
        <p className="text-slate-500 mt-1">Paste a git diff or enter a GitHub PR URL to detect ATO artifact impacts.</p>
      </div>

      {/* Input card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
        {/* System name */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">System Name (optional)</label>
          <input
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g. NCBI Datasets API"
            value={systemName}
            onChange={e => setSystemName(e.target.value)}
          />
        </div>

        {/* Mode toggle */}
        <div className="flex gap-2">
          {(['paste', 'url'] as const).map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                mode === m ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-600 border-slate-300 hover:border-blue-400'
              }`}
            >
              {m === 'paste' ? '📋 Paste Diff' : '🔗 PR URL'}
            </button>
          ))}
        </div>

        {mode === 'paste' ? (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Git Diff</label>
            <textarea
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-mono h-56 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
              placeholder={"Paste your git diff here...\n\ndiff --git a/requirements.txt b/requirements.txt\n--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1,3 +1,4 @@\n+stripe==6.0.0\n requests==2.28.0"}
              value={diffText}
              onChange={e => setDiffText(e.target.value)}
            />
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">GitHub PR URL</label>
            <input
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="https://github.com/owner/repo/pull/123"
              value={prUrl}
              onChange={e => setPrUrl(e.target.value)}
            />
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
            ⚠️ {error}
          </div>
        )}

        <button
          onClick={analyze}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <><span className="animate-spin">⟳</span> Analyzing…</>
          ) : (
            <><span>🔍</span> Analyze for ATO Impact</>
          )}
        </button>
      </div>

      {/* Results */}
      {result && (
        <ImpactReport
          result={result}
          onGenerateSIA={() => onAnalysisComplete(result.id)}
        />
      )}
    </div>
  )
}
