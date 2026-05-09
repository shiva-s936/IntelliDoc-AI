import { useState, useEffect } from 'react'
import { getHealth, getDocumentList, clearDocuments } from '../api'

function Slider({ label, value, min, max, step, onChange }) {
  return (
    <div className="mb-4">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{label}</span>
        <span className="text-violet-400 font-mono">{value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded appearance-none bg-slate-700 accent-violet-500 cursor-pointer"
      />
    </div>
  )
}

export default function Sidebar({ settings, onSettingsChange, onCollectionReset }) {
  const [health, setHealth] = useState(null)
  const [documents, setDocuments] = useState([])

  const refresh = async () => {
    try {
      const [h, d] = await Promise.all([getHealth(), getDocumentList()])
      setHealth(h.data)
      setDocuments(d.data.documents || [])
    } catch {
      setHealth(null)
    }
  }

  useEffect(() => { refresh() }, [])

  const handleClear = async () => {
    if (!confirm('Clear all indexed documents?')) return
    await clearDocuments()
    await refresh()
    onCollectionReset()
  }

  return (
    <aside className="w-64 shrink-0 bg-[#161b2e] border-r border-slate-800 flex flex-col h-screen sticky top-0 overflow-y-auto">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-white text-sm font-bold">
            ID
          </div>
          <div>
            <div className="text-sm font-semibold text-white">IntelliDoc AI</div>
            <div className="text-[11px] text-slate-500">Enterprise RAG</div>
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="px-5 py-4 border-b border-slate-800">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-3">System</div>
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'}`} />
          <span className="text-xs text-slate-300">{health?.status === 'healthy' ? 'API healthy' : 'API offline'}</span>
        </div>
        {health && (
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${health.api_keys_configured?.gemini ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <span className="text-xs text-slate-300">
              {health.api_keys_configured?.gemini ? 'Gemini connected' : 'Gemini key missing'}
            </span>
          </div>
        )}
      </div>

      {/* Indexed Documents */}
      <div className="px-5 py-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
            Indexed Docs
          </div>
          <span className="text-[11px] bg-violet-900/50 text-violet-300 px-1.5 py-0.5 rounded font-mono">
            {documents.length}
          </span>
        </div>
        {documents.length === 0 ? (
          <p className="text-xs text-slate-600 italic">No documents yet</p>
        ) : (
          <ul className="space-y-1">
            {documents.map((d, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-slate-400 truncate">
                <span className="text-slate-600">📄</span>
                <span className="truncate">{d.filename}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Retrieval Settings */}
      <div className="px-5 py-4 border-b border-slate-800">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-4">
          Retrieval
        </div>
        <Slider
          label="Top K"
          value={settings.topK}
          min={1} max={10} step={1}
          onChange={v => onSettingsChange({ ...settings, topK: v })}
        />
        <Slider
          label="Min Similarity"
          value={settings.similarityThreshold}
          min={0.0} max={0.9} step={0.05}
          onChange={v => onSettingsChange({ ...settings, similarityThreshold: v })}
        />
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-4 mt-2">
          Generation
        </div>
        <Slider
          label="Temperature"
          value={settings.temperature}
          min={0.0} max={1.0} step={0.1}
          onChange={v => onSettingsChange({ ...settings, temperature: v })}
        />
      </div>

      {/* Actions */}
      <div className="px-5 py-4 mt-auto">
        <button
          onClick={handleClear}
          className="w-full text-xs py-2 px-3 rounded-lg border border-red-900/50 text-red-400 hover:bg-red-900/20 transition-colors"
        >
          Reset Collection
        </button>
      </div>
    </aside>
  )
}
