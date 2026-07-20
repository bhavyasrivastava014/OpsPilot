import { useCallback, useEffect, useRef, useState } from 'react'

import {
  deleteDocument,
  listDocuments,
  previewDocument,
  type DocumentSummary,
} from '../../services/documentsApi'
import { getIndexName, notifyDocumentsChanged } from '../../services/session'
import { DocumentCard, type DocumentCardModel } from './DocumentCard'

function PreviewModal({
  indexName,
  documentId,
  filename,
  onClose,
}: {
  indexName: string
  documentId: string
  filename: string
  onClose: () => void
}) {
  const [pages, setPages] = useState<Array<{ page_number: number; chunks: Array<{ text: string }> }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  // Global listener for Escape key & clicks outside the content
  useEffect(() => {
    const handler = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent && e.key === 'Escape') {
        onClose()
        return
      }
      // Mouse click: close if click is outside the content panel
      if (e instanceof MouseEvent && contentRef.current) {
        const target = e.target as Node
        if (!contentRef.current.contains(target)) {
          onClose()
        }
      }
    }
    // Use capture phase to intercept before other handlers
    document.addEventListener('mousedown', handler, true)
    document.addEventListener('keydown', handler, true)
    return () => {
      document.removeEventListener('mousedown', handler, true)
      document.removeEventListener('keydown', handler, true)
    }
  }, [onClose])

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const res = await previewDocument(indexName, documentId)
        if (active) {
          setPages(res.pages)
          setError(null)
        }
      } catch {
        if (active) setError('Failed to load preview.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [indexName, documentId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div
        ref={contentRef}
        className="max-h-[80vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700/80 bg-slate-900 p-6 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-100">{filename}</h3>
          <button
            onClick={onClose}
            className="rounded-xl bg-rose-500/15 px-3 py-1.5 text-xs font-semibold text-rose-100 ring-1 ring-rose-500/20 transition hover:bg-rose-500/25 hover:ring-rose-500/30"
          >
            Close ✕
          </button>
        </div>

        {loading && <div className="text-sm text-slate-400">Loading preview…</div>}
        {error && <div className="text-sm text-rose-300">{error}</div>}

        {!loading && !error && pages.length === 0 && (
          <div className="text-sm text-slate-400">No text content found for this document.</div>
        )}

        {pages.map((page) => (
          <div key={page.page_number} className="mb-4 rounded-xl border border-slate-800/70 bg-slate-950/50 p-4">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
              Page {page.page_number}
            </div>
            {page.chunks.map((chunk, i) => (
              <p key={i} className="mb-2 text-sm leading-relaxed text-slate-200 last:mb-0">
                {chunk.text}
              </p>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export function DocumentList() {
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [previewDoc, setPreviewDoc] = useState<DocumentSummary | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const response = await listDocuments(getIndexName())
      setDocs(response.documents)
      setError(null)
    } catch {
      setError('Unable to load documents.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    const safeRefresh = async () => {
      if (!active) return
      await refresh()
    }
    const onDocumentsChanged = () => { void safeRefresh() }
    window.addEventListener('opspilot-documents-changed', onDocumentsChanged)
    void safeRefresh()
    return () => {
      active = false
      window.removeEventListener('opspilot-documents-changed', onDocumentsChanged)
    }
  }, [refresh])

  const handleDelete = useCallback(
    async (doc: DocumentCardModel) => {
      if (deletingId) return
      const confirmed = window.confirm(`Delete "${doc.filename}"? This cannot be undone.`)
      if (!confirmed) return

      setDeletingId(doc.id)
      try {
        const indexName = getIndexName()
        await deleteDocument(indexName, doc.id)
        notifyDocumentsChanged()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete document.')
      } finally {
        setDeletingId(null)
      }
    },
    [deletingId],
  )

  const handlePreview = useCallback((doc: DocumentCardModel) => {
    const found = docs.find((d) => d.document_id === doc.id)
    if (found) setPreviewDoc(found)
  }, [docs])

  const asCard = (doc: DocumentSummary): DocumentCardModel => ({
    id: doc.document_id,
    filename: doc.filename,
    pages: doc.pages ?? 0,
    status: doc.document_id === deletingId ? 'Processing' : 'Ready',
  })

  if (isLoading) return <div className="text-sm text-slate-400">Loading documents…</div>
  if (error) return <div className="rounded-lg bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>
  if (!docs.length) return <div className="text-sm text-slate-400">Upload PDFs from the sidebar to begin.</div>

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {docs.map((doc) => (
          <DocumentCard
            key={doc.document_id}
            doc={asCard(doc)}
            onPreview={handlePreview}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {previewDoc && (
        <PreviewModal
          indexName={getIndexName()}
          documentId={previewDoc.document_id}
          filename={previewDoc.filename}
          onClose={() => setPreviewDoc(null)}
        />
      )}
    </>
  )
}
