import { useEffect, useState } from 'react'

import { listDocuments, type DocumentSummary } from '../../services/documentsApi'
import { getIndexName } from '../../services/session'
import { DocumentCard, type DocumentCardModel } from './DocumentCard'

export function DocumentList() {
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const refresh = async () => {
      try {
        const response = await listDocuments(getIndexName())
        if (active) {
          setDocs(response.documents)
          setError(null)
        }
      } catch {
        if (active) setError('Unable to load documents.')
      } finally {
        if (active) setIsLoading(false)
      }
    }
    const onDocumentsChanged = () => { void refresh() }
    window.addEventListener('opspilot-documents-changed', onDocumentsChanged)
    void refresh()
    return () => {
      active = false
      window.removeEventListener('opspilot-documents-changed', onDocumentsChanged)
    }
  }, [])

  const asCard = (doc: DocumentSummary): DocumentCardModel => ({
    id: doc.document_id,
    filename: doc.filename,
    pages: doc.pages ?? 0,
    status: 'Ready',
  })

  if (isLoading) return <div className="text-sm text-slate-400">Loading documents…</div>
  if (error) return <div className="rounded-lg bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>
  if (!docs.length) return <div className="text-sm text-slate-400">Upload PDFs from the sidebar to begin.</div>

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {docs.map((doc) => (
        <DocumentCard key={doc.document_id} doc={asCard(doc)} />
      ))}
    </div>
  )
}
