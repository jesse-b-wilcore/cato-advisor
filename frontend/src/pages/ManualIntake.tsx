import { useState, useEffect } from 'react'

interface Props {
  onChangeSubmitted: (changeId: string) => void
}

export default function ManualIntake({ onChangeSubmitted }: Props) {
  const [changeTypes, setChangeTypes] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [freeText, setFreeText] = useState('')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [classifying, setClassifying] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [classified, setClassified] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    fetch('/api/intake/types').then(r => r.json()).then(setChangeTypes)
  }, [])

  const classifyText = async () => {
    if (!freeText.trim()) return
    setClassifying(true)
    setError(null)
    try {
      const res = await fetch('/api/intake/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: freeText }),
      })
      const data = await res.json()
      setClassified(data)
      const match = changeTypes.find(t => t.id === data.change_type_id)
      if (match) {
        setSelected(match)
        setFormData(data.extracted_fields || {})
      }
    } catch {
      setError('Classification failed — try selecting a change type manually.')
    } finally {
      setClassifying(false)
    }
  }

  const submit = async () => {
    if (!selected) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch('/api/intake/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ change_type_id: selected.id, form_data: formData }),
      })
      if (!res.ok) {
        const e = await res.json()
        throw new Error(e.detail)
      }
      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const TIER_COLORS: Record<string, string> = { green: 'text-green-700', yellow: 'text-yellow-700', orange: 'text-orange-700', red: 'text-red-700' }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Manual Change Intake</h2>
        <p className="text-slate-500 mt-1">Report non-code system changes — organizational, policy, physical, or scope changes.</p>
      </div>

      {/* AI description */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
        <h3 className="font-semibold text-slate-700">Describe the change in plain English</h3>
        <textarea
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm h-24 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder="e.g. We're switching from Vendor A to Vendor B for our cloud hosting. They'll have access to system data."
          value={freeText}
          onChange={e => setFreeText(e.target.value)}
        />
        <button onClick={classifyText} disabled={classifying || !freeText.trim()}
          className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
          {classifying ? '⟳ Classifying…' : '✨ Classify with AI'}
        </button>
        {classified && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg px-4 py-3 text-sm text-purple-800">
            Classified as <strong>{classified.change_type_name}</strong> (confidence: {classified.confidence})
            {classified.reasoning && <div className="text-xs mt-1 opacity-75">{classified.reasoning}</div>}
          </div>
        )}
      </div>

      {/* Manual selector */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
        <h3 className="font-semibold text-slate-700">Or select a change type</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {changeTypes.map(ct => (
            <button key={ct.id} onClick={() => { setSelected(ct); setFormData({}) }}
              className={`text-left p-3 rounded-lg border text-sm transition-colors ${
                selected?.id === ct.id ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-blue-300'
              }`}>
              <div className="font-medium text-slate-800">{ct.name}</div>
              <div className="text-xs text-slate-500 mt-0.5">{ct.example}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Form */}
      {selected && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <h3 className="font-semibold text-slate-700">{selected.name} — Details</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {selected.form_fields?.map((field: string) => (
              <div key={field}>
                <label className="block text-sm font-medium text-slate-600 mb-1 capitalize">
                  {field.replace(/_/g, ' ')}
                </label>
                <input
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData[field] || ''}
                  onChange={e => setFormData(p => ({ ...p, [field]: e.target.value }))}
                />
              </div>
            ))}
          </div>
          {error && <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">⚠️ {error}</div>}
          <button onClick={submit} disabled={submitting}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 rounded-lg transition-colors">
            {submitting ? '⟳ Analyzing…' : '📊 Analyze ATO Impact'}
          </button>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className={`rounded-xl border-2 p-5 space-y-4 ${
          result.tier?.color === 'red' ? 'bg-red-50 border-red-300' :
          result.tier?.color === 'orange' ? 'bg-orange-50 border-orange-300' :
          result.tier?.color === 'yellow' ? 'bg-yellow-50 border-yellow-300' :
          'bg-green-50 border-green-300'
        }`}>
          <div className="font-bold text-lg">Tier: {result.tier?.name} — {result.tier?.ao_action}</div>
          <div className="text-sm text-slate-600">
            {result.total_artifact_count} artifacts affected · {result.total_control_count} controls affected
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-700 mb-2">Affected Artifacts:</p>
            <div className="flex flex-wrap gap-2">
              {result.affected_artifacts?.map((a: any) => (
                <span key={a.id} className="bg-white border border-slate-200 rounded px-2 py-1 text-xs">
                  <strong>{a.id}</strong> {a.name}
                </span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-700 mb-2">Recommended Actions:</p>
            <ul className="space-y-1">
              {result.recommended_actions?.map((a: string, i: number) => (
                <li key={i} className="text-sm text-slate-700 flex gap-2"><span className="text-blue-500">→</span>{a}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
