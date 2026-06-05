import { useState } from 'react'

interface Props {
  analysisId: string | null
  siaId: string | null
  onSiaGenerated: (siaId: string) => void
}

const RISK_COLORS: Record<string, string> = {
  Low:      'text-green-700 bg-green-50  border-green-300',
  Moderate: 'text-yellow-700 bg-yellow-50 border-yellow-300',
  High:     'text-red-700    bg-red-50    border-red-300',
}

export default function SIAViewer({ analysisId, siaId, onSiaGenerated }: Props) {
  const [systemName, setSystemName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sia, setSia] = useState<any>(null)

  const generate = async () => {
    if (!analysisId && !siaId) {
      setError('Run a diff analysis first (UC1) or submit a manual change (UC2).')
      return
    }
    setLoading(true)
    setError(null)

    try {
      let data: any
      if (siaId) {
        const res = await fetch(`/api/documents/sia/${siaId}`)
        data = await res.json()
        setSia(data)
        return
      }

      const res = await fetch('/api/documents/sia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: analysisId, system_name: systemName || '[System Name]' }),
      })
      if (!res.ok) {
        const e = await res.json(); throw new Error(e.detail)
      }
      data = await res.json()
      setSia(data)
      onSiaGenerated(data.sia_id)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const downloadDocx = async () => {
    if (!sia?.sia_id) return
    const res = await fetch(`/api/documents/sia/${sia.sia_id}/docx`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `SIA-${sia.system_name?.replace(/ /g, '_')}-${sia.change_reference}-${new Date().toISOString().split('T')[0]}.docx`
    a.click()
    URL.revokeObjectURL(url)
  }

  const TIER_COLORS: Record<string, string> = { green: 'text-green-700', yellow: 'text-yellow-700', orange: 'text-orange-700', red: 'text-red-700' }
  const TIER_BG: Record<string, string> = { green: 'bg-green-50 border-green-300', yellow: 'bg-yellow-50 border-yellow-300', orange: 'bg-orange-50 border-orange-300', red: 'bg-red-50 border-red-300' }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">SIA Generator</h2>
        <p className="text-slate-500 mt-1">Auto-generate a draft Security Impact Analysis from a classified change.</p>
      </div>

      {!sia && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          {!analysisId && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
              ⓘ No analysis loaded. Go to <strong>Diff Analyzer</strong> (UC1) or <strong>Manual Intake</strong> (UC2) first, then return here.
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">System Name</label>
            <input className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. NCBI Datasets API"
              value={systemName}
              onChange={e => setSystemName(e.target.value)}
            />
          </div>
          {error && <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded p-3">⚠️ {error}</div>}
          <button onClick={generate} disabled={loading || !analysisId}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 rounded-lg transition-colors">
            {loading ? '⟳ Generating SIA with Claude…' : '📄 Generate Security Impact Analysis'}
          </button>
        </div>
      )}

      {sia && (
        <div className="space-y-4">
          {/* Document header */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h3 className="text-xl font-bold text-slate-800">Security Impact Analysis</h3>
                <p className="text-slate-500 text-sm mt-0.5">FOR OFFICIAL USE ONLY — AI-ASSISTED DRAFT</p>
                <div className="flex gap-4 mt-3 text-sm text-slate-600">
                  <span><strong>System:</strong> {sia.system_name}</span>
                  <span><strong>Change Ref:</strong> {sia.change_reference}</span>
                  <span><strong>Date:</strong> {sia.prepared_date || new Date().toLocaleDateString()}</span>
                </div>
              </div>
              <button onClick={downloadDocx}
                className="shrink-0 bg-slate-800 hover:bg-slate-700 text-white font-medium px-5 py-2.5 rounded-lg text-sm flex items-center gap-2 transition-colors">
                ⬇️ Download DOCX
              </button>
            </div>

            {/* Tier + risk row */}
            <div className="flex gap-3 mt-4 flex-wrap">
              <span className={`px-3 py-1.5 rounded-lg border text-sm font-semibold ${TIER_BG[sia.tier_color]}`}>
                Tier: {sia.tier}
              </span>
              <span className={`px-3 py-1.5 rounded-lg border text-sm font-semibold ${RISK_COLORS[sia.risk_level] || RISK_COLORS.Moderate}`}>
                Risk: {sia.risk_level}
              </span>
              <span className="px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-700">
                AO Action: <strong>{sia.ao_action_required}</strong>
              </span>
            </div>
          </div>

          {/* Sections */}
          {[
            { num: '2', title: 'Change Description', content: sia.change_description },
            { num: '3', title: 'System Impact Summary', content: sia.system_impact_summary },
            { num: '6', title: 'Risk Determination', content: sia.risk_determination },
          ].map(s => s.content && (
            <div key={s.num} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h4 className="font-semibold text-slate-700 mb-2">{s.num}. {s.title}</h4>
              <p className="text-sm text-slate-700 leading-relaxed">{s.content}</p>
            </div>
          ))}

          {/* Controls analysis */}
          {sia.affected_controls_analysis?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h4 className="font-semibold text-slate-700 mb-3">4. Affected Controls Analysis</h4>
              <div className="space-y-3">
                {sia.affected_controls_analysis.map((c: any, i: number) => (
                  <div key={i} className="border border-slate-100 rounded-lg p-4 bg-slate-50">
                    <div className="font-medium text-slate-800 text-sm">{c.control_id} — {c.control_title}</div>
                    <div className="text-xs text-slate-600 mt-1"><strong>Impact:</strong> {c.impact_description}</div>
                    {c.required_update && (
                      <div className="text-xs text-blue-700 mt-1"><strong>Required SSP Update:</strong> {c.required_update}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Artifacts */}
          {sia.affected_artifacts?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h4 className="font-semibold text-slate-700 mb-3">5. Affected Artifacts</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b border-slate-200">
                      {['ID', 'Artifact', 'Phase', 'Urgency'].map(h => (
                        <th key={h} className="pb-2 pr-4 font-semibold text-slate-600">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sia.affected_artifacts.map((a: any) => (
                      <tr key={a.id} className="border-b border-slate-50">
                        <td className="py-2 pr-4 font-mono text-xs font-bold text-blue-700">{a.id}</td>
                        <td className="py-2 pr-4 text-slate-700">{a.name}</td>
                        <td className="py-2 pr-4 text-slate-500 text-xs">{a.phase}</td>
                        <td className="py-2">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            a.urgency === 'immediate' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                          }`}>{a.urgency}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Recommended actions */}
          {sia.recommended_actions?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <h4 className="font-semibold text-slate-700 mb-3">7. Recommended Actions</h4>
              <ul className="space-y-2">
                {sia.recommended_actions.map((a: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="text-blue-500 shrink-0 mt-0.5">→</span>{a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Signature block */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h4 className="font-semibold text-slate-700 mb-3">8. Approval Signatures</h4>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  {['Role', 'Name / Signature', 'Date'].map(h => (
                    <th key={h} className="pb-2 pr-6 text-left font-semibold text-slate-600">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {['ISSO', 'ISSM', 'Authorizing Official (AO)'].map(role => (
                  <tr key={role} className="border-b border-slate-50">
                    <td className="py-3 pr-6 text-slate-700">{role}</td>
                    <td className="py-3 pr-6 text-slate-300 text-xs italic">_____________________________</td>
                    <td className="py-3 text-slate-300 text-xs italic">____________</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="text-xs text-slate-400 text-center pb-4">
            AI-assisted draft — requires ISSO review and validation before submission · cATO Advisor v0.1
          </div>

          <button onClick={() => setSia(null)}
            className="w-full border border-slate-300 text-slate-600 font-medium py-2.5 rounded-lg hover:bg-slate-50 transition-colors text-sm">
            ← Generate New SIA
          </button>
        </div>
      )}
    </div>
  )
}
