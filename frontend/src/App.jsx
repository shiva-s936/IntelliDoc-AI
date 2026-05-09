import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import UploadTab from './components/UploadTab'
import QATab from './components/QATab'
import EvaluationTab from './components/EvaluationTab'
import { getDocumentInfo } from './api'

const TABS = [
  { id: 'upload', label: 'Upload', icon: '📁' },
  { id: 'qa', label: 'Q & A', icon: '💬' },
  { id: 'evaluate', label: 'Evaluate', icon: '📊' },
]

export default function App() {
  const [tab, setTab] = useState('upload')
  const [settings, setSettings] = useState({
    topK: 5,
    similarityThreshold: 0.1,
    temperature: 0.3,
  })
  const [hasDocuments, setHasDocuments] = useState(false)
  const [qaHistory, setQAHistory] = useState([])
  const [sidebarRefresh, setSidebarRefresh] = useState(0)

  // On mount, check if docs already exist in the vector store
  useEffect(() => {
    getDocumentInfo()
      .then(res => {
        if (res.data?.info?.document_count > 0) setHasDocuments(true)
      })
      .catch(() => {})
  }, [])

  const handleUploaded = () => {
    setHasDocuments(true)
    setSidebarRefresh(n => n + 1)
  }

  const handleCollectionReset = () => {
    setHasDocuments(false)
    setQAHistory([])
  }

  const handleQAComplete = item => {
    setQAHistory(h => [...h, item])
  }

  return (
    <div className="flex min-h-screen bg-[#0f1117]">
      <Sidebar
        key={sidebarRefresh}
        settings={settings}
        onSettingsChange={setSettings}
        onCollectionReset={handleCollectionReset}
      />

      <div className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="border-b border-slate-800 px-8 py-0 flex items-center bg-[#0f1117] sticky top-0 z-10">
          <nav className="flex gap-1">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-4 text-sm font-medium border-b-2 transition-colors
                  ${tab === t.id
                    ? 'border-violet-500 text-white'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
              >
                <span>{t.icon}</span>
                {t.label}
              </button>
            ))}
          </nav>
          <div className="ml-auto text-xs text-slate-600">
            IntelliDoc AI · FastAPI + ChromaDB + Gemini
          </div>
        </header>

        {/* Content */}
        <main className={`flex-1 px-8 py-8 ${tab === 'qa' ? 'flex flex-col' : ''}`}>
          {tab === 'upload' && <UploadTab onUploaded={handleUploaded} />}
          {tab === 'qa' && (
            <QATab
              settings={settings}
              hasDocuments={hasDocuments}
              onQAComplete={handleQAComplete}
            />
          )}
          {tab === 'evaluate' && <EvaluationTab qaHistory={qaHistory} />}
        </main>
      </div>
    </div>
  )
}
