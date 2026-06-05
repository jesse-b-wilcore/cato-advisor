const TIER_CONFIG: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  green:  { bg: 'bg-green-50',  text: 'text-green-800',  border: 'border-green-300', icon: '🟢' },
  yellow: { bg: 'bg-yellow-50', text: 'text-yellow-800', border: 'border-yellow-300', icon: '🟡' },
  orange: { bg: 'bg-orange-50', text: 'text-orange-800', border: 'border-orange-300', icon: '🟠' },
  red:    { bg: 'bg-red-50',    text: 'text-red-800',    border: 'border-red-300',    icon: '🔴' },
}

const CONFIDENCE_BADGE: Record<string, string> = {
  high:   'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low:    'bg-slate-100 text-slate-600',
}

interface Props {
  result: any
  onGenerateSIA: () => void
}

export default function ImpactReport({ result, onGenerateSIA }: Props) {
  const tier = result.tier || {}
  const tc = TIER_CONFIG[tier.color] || TIER_CONFIG.green

  const immediateArtifacts = result.affected_artifacts?.filter((a: any) => a.urgency === 'immediate') || []
  const reviewArtifacts    = result.affected_artifacts?.filter((a: any) => a.urgency === 'review') || []

  return (
    <div className="space-y-4">
      {/* Tier banner */}
      <div className={`rounded-xl border-2 ${tc.bg} ${tc.border} p-5`}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className={`text-2xl font-bold ${tc.text} flex items-center gap-2`}>
              {tc.icon} {tier.name}
            </div>
            <div className={`text-sm mt-1 ${tc.text} opacity-80`}>
              AO Action Required: <strong>{tier.ao_action || 'None'}</strong>
            </div>
            {tier.ao_action_description && (
              <div className={`text-xs mt-1 ${tc.text} opacity-70`}>{tier.ao_action_description}</div>
            )}
          </div>
          <div className="text-right text-sm text-slate-500">
            <div>{result.diff_stats?.file_count ?? 0} files changed</div>
            <div>{result.total_artifact_count} artifacts affected</div>
            <div>{result.total_control_count} controls affected</div>
          </div>
        </div>
      </div>

      {/* Detected changes */}
      {result.detected_changes?.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-slate-700 mb-3">🔎 Detected Change Types</h3>
          <div className="space-y-2">
            {result.detected_changes.map((c: any, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800 text-sm">{c.change_type_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CONFIDENCE_BADGE[c.confidence] || CONFIDENCE_BADGE.low}`}>
                      {c.confidence}
                    </span>
                    {c.source === 'llm' && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">AI classified</span>
                    )}
                  </div>
                  {c.evidence?.length > 0 && (
                    <div className="text-xs text-slate-500 mt-1">{c.evidence.slice(0, 2).join(' · ')}</div>
                  )}
                  {c.llm_reasoning && (
                    <div className="text-xs text-purple-600 mt-1 italic">{c.llm_reasoning}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Artifacts */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-slate-700 mb-3">📁 Affected Artifacts</h3>
          {result.affected_artifacts?.length === 0 ? (
            <p className="text-sm text-slate-400">No artifacts affected.</p>
          ) : (
            <div className="space-y-2">
              {immediateArtifacts.length > 0 && (
                <>
                  <p className="text-xs font-semibold text-red-600 uppercase tracking-wide">Immediate Update Required</p>
                  {immediateArtifacts.map((a: any) => (
                    <div key={a.id} className="flex items-start gap-2 p-2 bg-red-50 rounded border border-red-100">
                      <span className="text-xs font-mono text-red-700 font-bold mt-0.5 shrink-0">{a.id}</span>
                      <span className="text-sm text-slate-700">{a.name}</span>
                    </div>
                  ))}
                </>
              )}
              {reviewArtifacts.length > 0 && (
                <>
                  <p className="text-xs font-semibold text-yellow-600 uppercase tracking-wide mt-3">Review Recommended</p>
                  {reviewArtifacts.map((a: any) => (
                    <div key={a.id} className="flex items-start gap-2 p-2 bg-yellow-50 rounded border border-yellow-100">
                      <span className="text-xs font-mono text-yellow-700 font-bold mt-0.5 shrink-0">{a.id}</span>
                      <span className="text-sm text-slate-700">{a.name}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-slate-700 mb-3">🔐 Affected NIST 800-53 Controls</h3>
          {result.affected_controls?.length === 0 ? (
            <p className="text-sm text-slate-400">No controls affected.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {result.affected_controls.map((c: any) => (
                <span key={c.id} className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 border border-blue-200 rounded-lg px-3 py-1.5 text-xs font-medium" title={c.title}>
                  <span className="font-bold">{c.id}</span>
                  <span className="opacity-70">{c.title}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recommended actions */}
      {result.recommended_actions?.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="font-semibold text-slate-700 mb-3">✅ Recommended Actions</h3>
          <ul className="space-y-2">
            {result.recommended_actions.map((action: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="text-blue-500 mt-0.5 shrink-0">→</span>
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Generate SIA CTA */}
      {result.detected_changes?.length > 0 && tier.id !== 'ROUTINE' && (
        <div className="bg-slate-900 rounded-xl p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-white font-semibold">Ready to generate a Security Impact Analysis?</p>
            <p className="text-slate-400 text-sm mt-1">Auto-draft a complete SIA document for ISSO review and AO submission.</p>
          </div>
          <button
            onClick={onGenerateSIA}
            className="shrink-0 bg-blue-500 hover:bg-blue-400 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
          >
            Generate SIA →
          </button>
        </div>
      )}
    </div>
  )
}
