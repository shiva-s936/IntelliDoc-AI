import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { askQuestion } from '../api'

function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-slate-700/60 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-800/40 hover:bg-slate-800/70 transition-colors text-left"
      >
        <span className="text-slate-400 font-medium">Source {source.source_id}</span>
        <span className="text-slate-600">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 py-2.5 text-slate-400 leading-relaxed bg-slate-900/30">
          <p>{source.content_preview}</p>
          {source.metadata?.filename && (
            <p className="text-slate-600 mt-2">📄 {source.metadata.filename}</p>
          )}
        </div>
      )}
    </div>
  )
}

function Message({ item }) {
  const [showSources, setShowSources] = useState(false)
  return (
    <div className="mb-6">
      {/* Question bubble */}
      <div className="flex justify-end mb-3">
        <div className="max-w-[80%] bg-violet-700/30 border border-violet-700/40 rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="text-sm text-violet-100">{item.question}</p>
        </div>
      </div>
      {/* Answer bubble */}
      <div className="flex justify-start">
        <div className="max-w-[85%]">
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
            <div className="text-sm text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{item.answer}</ReactMarkdown>
            </div>
            {item.processing_time && (
              <p className="text-[11px] text-slate-600 mt-2">{item.processing_time.toFixed(2)}s</p>
            )}
          </div>
          {item.sources?.length > 0 && (
            <div className="mt-2">
              <button
                onClick={() => setShowSources(o => !o)}
                className="text-xs text-slate-500 hover:text-violet-400 transition-colors"
              >
                {showSources ? '▲ Hide' : '▼ Show'} {item.sources.length} source{item.sources.length > 1 ? 's' : ''}
              </button>
              {showSources && (
                <div className="mt-2 space-y-1.5">
                  {item.sources.map((s, i) => <SourceCard key={i} source={s} index={i} />)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function QATab({ settings, hasDocuments, onQAComplete }) {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const bottomRef = useRef()
  const inputRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const submit = async () => {
    const q = question.trim()
    if (!q || loading) return
    setQuestion('')
    setError(null)
    setLoading(true)
    try {
      const res = await askQuestion(q, settings)
      const item = res.data
      setHistory(h => [...h, item])
      onQAComplete(item)
    } catch (e) {
      setError(e.response?.data?.detail || 'Request failed.')
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-white mb-1">Ask Questions</h2>
        <p className="text-sm text-slate-400">Answers are grounded in your indexed documents</p>
      </div>

      {!hasDocuments && (
        <div className="bg-amber-900/20 border border-amber-800/40 rounded-lg px-4 py-3 text-sm text-amber-400 mb-4">
          Upload and process a document first to enable Q&A.
        </div>
      )}

      {/* Message history */}
      <div className="flex-1 overflow-y-auto mb-4 min-h-0">
        {history.length === 0 && hasDocuments && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="text-4xl mb-3">💬</div>
            <p className="text-slate-300 font-medium mb-1">Ask anything about your documents</p>
            <p className="text-slate-500 text-xs mb-6">Try one of these to get started</p>
            <div className="grid grid-cols-2 gap-2 max-w-lg w-full">
              {[
                'Summarise this document',
                'What are the key skills?',
                'What is the work experience?',
                'What projects are mentioned?',
              ].map(q => (
                <button
                  key={q}
                  onClick={() => { setQuestion(q); inputRef.current?.focus() }}
                  className="text-left text-xs text-slate-400 bg-slate-800/50 border border-slate-700/50 rounded-lg px-3 py-2.5 hover:border-violet-600/50 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {history.map((item, i) => <Message key={i} item={item} />)}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mb-3 bg-red-900/20 border border-red-800/50 rounded-lg px-4 py-2.5 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 items-end">
        <textarea
          ref={inputRef}
          rows={2}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKey}
          disabled={!hasDocuments || loading}
          placeholder={hasDocuments ? 'Ask a question… (Enter to send)' : 'Upload a document to start'}
          className="flex-1 resize-none bg-slate-800/60 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-600 disabled:opacity-40 transition-colors"
        />
        <button
          onClick={submit}
          disabled={!question.trim() || !hasDocuments || loading}
          className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white px-5 py-3 rounded-xl font-medium text-sm transition-colors shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  )
}
