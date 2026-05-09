import { useState } from 'react'
import { runEvaluation } from '../api'

function ScoreBar({ label, score, description }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  const textColor = pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400'
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-sm font-semibold text-white capitalize">{label.replace('_', ' ')}</div>
          <div className="text-xs text-slate-500 mt-0.5 max-w-xs">{description}</div>
        </div>
        <div className={`text-2xl font-bold font-mono ${textColor}`}>{pct}%</div>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

const METRIC_INFO = {
  faithfulness: 'Fraction of answer claims supported by the retrieved context — detects hallucinations.',
  answer_relevancy: 'How well the answer addresses the question asked.',
}

export default function EvaluationTab({ qaHistory }) {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const res = await runEvaluation(qaHistory)
      setResults(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Evaluation failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-white mb-1">RAGAS Evaluation</h2>
      <p className="text-sm text-slate-400 mb-6">
        Measures answer quality using Google Gemini as the judge — no ground truth required.
      </p>

      {qaHistory.length === 0 ? (
        <div className="bg-amber-900/20 border border-amber-800/40 rounded-lg px-4 py-3 text-sm text-amber-400">
          Ask some questions first — evaluation runs on your Q&amp;A history.
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between bg-slate-800/40 border border-slate-700/50 rounded-xl px-5 py-4 mb-6">
            <div>
              <div className="text-sm font-medium text-white">Ready to evaluate</div>
              <div className="text-xs text-slate-500 mt-0.5">
                {qaHistory.length} question{qaHistory.length > 1 ? 's' : ''} in history
              </div>
            </div>
            <button
              onClick={handleRun}
              disabled={loading}
              className="bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm px-5 py-2.5 rounded-lg font-medium transition-colors"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Evaluating…
                </span>
              ) : 'Run RAGAS'}
            </button>
          </div>

          {error && (
            <div className="mb-4 bg-red-900/20 border border-red-800/50 rounded-lg px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {results && (
            <div>
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium mb-5">
                <span>✓</span> Evaluation complete
              </div>

              <div className="space-y-3 mb-6">
                {Object.entries(results.overall_scores || {}).map(([key, score]) => (
                  <ScoreBar
                    key={key}
                    label={key}
                    score={score}
                    description={METRIC_INFO[key] || ''}
                  />
                ))}
              </div>

              {results.summary && (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl px-5 py-4">
                  <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Summary</div>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { label: 'Average Score', value: `${(results.summary.average_score * 100).toFixed(1)}%` },
                      { label: 'Questions', value: results.summary.total_questions },
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <div className="text-xs text-slate-500">{label}</div>
                        <div className="text-sm font-semibold text-white mt-0.5">{value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
