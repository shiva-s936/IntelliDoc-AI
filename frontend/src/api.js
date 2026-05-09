import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getHealth = () => api.get('/health')
export const getDocumentInfo = () => api.get('/documents/info')
export const getDocumentList = () => api.get('/documents/list')
export const clearDocuments = () => api.delete('/documents/clear')

export const uploadDocument = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress && onProgress(Math.round((e.loaded * 100) / e.total)),
  })
}

export const askQuestion = (question, settings) =>
  api.post('/questions/ask', {
    question,
    top_k: settings.topK,
    similarity_threshold: settings.similarityThreshold,
    temperature: settings.temperature,
    include_sources: true,
  })

export const runEvaluation = (qaHistory) => {
  const questions = qaHistory.map(r => r.question)
  const answers = qaHistory.map(r => r.answer)
  // context_used is the full context string stored by QAChain
  const contexts = qaHistory.map(r => r.context_used || '')
  return api.post('/evaluation/run', { questions, answers, contexts })
}
