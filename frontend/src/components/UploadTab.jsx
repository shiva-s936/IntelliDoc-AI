import { useState, useRef } from 'react'
import { uploadDocument } from '../api'

export default function UploadTab({ onUploaded }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef()

  const accept = f => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['pdf', 'txt'].includes(ext)) {
      setError('Only PDF and TXT files are supported.')
      return
    }
    setFile(f)
    setResult(null)
    setError(null)
  }

  const handleDrop = e => {
    e.preventDefault()
    setDragging(false)
    accept(e.dataTransfer.files[0])
  }

  const handleProcess = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    setProgress(0)
    try {
      const res = await uploadDocument(file, setProgress)
      setResult(res.data)
      onUploaded()
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-white mb-1">Upload Document</h2>
      <p className="text-sm text-slate-400 mb-6">PDF or TXT — chunks are embedded and stored in ChromaDB</p>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
          ${dragging ? 'border-violet-500 bg-violet-900/10' : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/30'}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          className="hidden"
          onChange={e => accept(e.target.files[0])}
        />
        <div className="text-4xl mb-3">📄</div>
        <p className="text-sm text-slate-300 font-medium">
          {file ? file.name : 'Drop a file here or click to browse'}
        </p>
        <p className="text-xs text-slate-500 mt-1">
          {file ? `${(file.size / 1024).toFixed(1)} KB` : 'PDF · TXT'}
        </p>
      </div>

      {/* File selected */}
      {file && !result && (
        <div className="mt-4 flex items-center justify-between bg-slate-800/50 rounded-lg px-4 py-3">
          <div className="text-sm text-slate-300 truncate mr-4">{file.name}</div>
          <button
            onClick={handleProcess}
            disabled={loading}
            className="shrink-0 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm px-5 py-2 rounded-lg font-medium transition-colors"
          >
            {loading ? 'Processing…' : 'Process'}
          </button>
        </div>
      )}

      {/* Progress bar */}
      {loading && (
        <div className="mt-3 h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-violet-500 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 bg-red-900/20 border border-red-800/50 rounded-lg px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mt-4 bg-emerald-900/20 border border-emerald-800/40 rounded-xl px-5 py-4">
          <div className="flex items-center gap-2 text-emerald-400 font-medium mb-4">
            <span>✓</span> Processed successfully
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Chunks', value: result.chunks_created },
              { label: 'File', value: result.filename?.split('.').pop()?.toUpperCase() },
              { label: 'Status', value: result.success ? 'Indexed' : 'Failed' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-slate-800/60 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">{value}</div>
                <div className="text-xs text-slate-500 mt-0.5">{label}</div>
              </div>
            ))}
          </div>
          <button
            onClick={() => { setFile(null); setResult(null) }}
            className="mt-4 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Upload another
          </button>
        </div>
      )}
    </div>
  )
}
