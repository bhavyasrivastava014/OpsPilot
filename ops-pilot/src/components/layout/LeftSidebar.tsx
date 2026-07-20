import { useEffect, useMemo, useRef, useState } from 'react'
import { ingestPdfs, listDocuments, type UploadError, type DocumentSummary } from '../../services/documentsApi'
import { getIndexName, notifyDocumentsChanged } from '../../services/session'

const INDEX_NAME = getIndexName()

export function LeftSidebar() {
  const inputRef = useRef<HTMLInputElement | null>(null)

  const [isUploading, setIsUploading] = useState(false)
  const [errors, setErrors] = useState<UploadError[]>([])
  const [docs, setDocs] = useState<DocumentSummary[]>([])

  async function refreshDocs() {
    try {
      const resp = await listDocuments(INDEX_NAME)
      setDocs(resp.documents)
    } catch {
      // keep existing docs
    }
  }

  useEffect(() => {
    let active = true
    void listDocuments(INDEX_NAME)
      .then((resp) => {
        if (active) setDocs(resp.documents)
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [])

  const totalLabel = useMemo(() => {
    return `${docs.length} total`
  }, [docs.length])

  function openFilePicker() {
    inputRef.current?.click()
  }

  function validatePdfFiles(fileList: FileList | null): File[] {
    if (!fileList || fileList.length === 0) return []
    const files = Array.from(fileList)
    return files.filter((f) => f.name.toLowerCase().endsWith('.pdf'))
  }

  async function handleFiles(files: File[]) {
    if (files.length === 0) {
      setErrors([{ filename: 'selected files', error: 'Only .pdf files are allowed.' }])
      return
    }

    setErrors([])
    setIsUploading(true)

    try {
      const resp = await ingestPdfs(files, INDEX_NAME)
      if ('ok' in resp && resp.ok === false) {
        setErrors(resp.errors)
        return
      }

      await refreshDocs()
      notifyDocumentsChanged()
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Upload failed'
      setErrors([{ filename: 'upload', error: msg }])
    } finally {
      setIsUploading(false)
    }
  }

  function onInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    void handleFiles(Array.from(e.target.files ?? []).filter((f) => f.name.toLowerCase().endsWith('.pdf')))
    // allow selecting the same file again
    if (inputRef.current) inputRef.current.value = ''
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    void handleFiles(validatePdfFiles(e.dataTransfer.files))
  }

  return (
    <aside className="flex h-full w-full flex-col border-r border-slate-800/70 bg-slate-950/40 backdrop-blur">
      {/* Header */}
      <div className="px-5 pb-4 pt-5">
        <div className="text-sm font-semibold text-slate-200">OpsPilot</div>
        <div className="mt-1 text-xs font-medium text-slate-400">Document Intelligence Assistant</div>
      </div>

      {/* Upload Area */}
      <div className="px-5">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          onChange={onInputChange}
        />

        <div
          className="group flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-800/70 bg-slate-950/30 px-4 py-6 text-center transition-colors hover:bg-slate-950/50"
          role="button"
          tabIndex={0}
          aria-label="Upload PDFs"
          onClick={() => {
            if (!isUploading) openFilePicker()
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              if (!isUploading) openFilePicker()
            }
          }}
          onDragOver={onDragOver}
          onDrop={onDrop}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/15 ring-1 ring-indigo-500/20">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5 text-indigo-200"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>

          <div className="text-sm font-semibold text-slate-200">Upload PDFs</div>
          <div className="text-xs text-slate-400">{isUploading ? 'Uploading…' : 'Drag & drop PDFs here'}</div>
        </div>

        {errors.length ? (
          <div className="mt-3 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3">
            <div className="mb-2 text-xs font-semibold text-rose-200">Upload errors</div>
            <ul className="space-y-1 text-xs text-rose-100/80">
              {errors.map((e, idx) => (
                <li key={`${e.filename}_${idx}`}>• {e.filename}: {e.error}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      {/* Loaded Documents */}
      <div className="mt-6 flex min-h-0 flex-1 flex-col px-5 pb-4">
        <div className="flex items-center justify-between gap-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <span>Loaded Documents</span>
          <span className="font-normal normal-case text-slate-400">{totalLabel}</span>
        </div>

        <div className="mt-3 flex-1 overflow-auto rounded-xl border border-slate-800/70 bg-slate-950/25 p-4">
          {docs.length === 0 ? (
            <div className="text-sm font-medium text-slate-400">No documents uploaded.</div>
          ) : (
            <ul className="space-y-2">
              {docs.map((d) => (
                <li key={d.document_id} className="rounded-lg border border-slate-800/70 bg-slate-950/20 p-2">
                  <div className="truncate text-xs font-medium text-slate-100">{d.filename}</div>
                  <div className="mt-1 text-[11px] text-slate-400">
                    Pages: {d.pages ?? 'unknown'}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-800/70 px-5 py-4">
        <div className="text-xs text-slate-400">Grounded AI Assistant</div>
      </div>
    </aside>
  )
}

