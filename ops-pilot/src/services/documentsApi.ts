import { buildApiUrl } from './api'

export type UploadError = { filename: string; error: string }

export type UploadResponse =
  | { ok: true; index_name: string; documents: DocumentSummary[] }
  | { ok: false; errors: UploadError[] }

export type DocumentSummary = {
  document_id: string
  filename: string
  pages: number | null
}

export type ListDocumentsResponse = {
  ok: boolean
  index_name: string
  timestamp: string
  documents: DocumentSummary[]
}

export async function listDocuments(indexName: string = 'default'): Promise<ListDocumentsResponse> {
  const res = await fetch(buildApiUrl(`/documents?index_name=${encodeURIComponent(indexName)}`))
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to list documents: ${res.status} ${text}`)
  }
  return res.json()
}


export async function deleteDocument(indexName: string, documentId: string): Promise<{ ok: boolean; chunks_deleted: number }> {
  const res = await fetch(buildApiUrl(`/documents/${encodeURIComponent(indexName)}/${encodeURIComponent(documentId)}`), {
    method: 'DELETE',
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to delete document: ${res.status} ${text}`)
  }
  return res.json()
}

export type PreviewPage = {
  page_number: number
  chunks: Array<{ chunk_id: string; text: string; chunk_index: number }>
}

export type PreviewResponse = {
  ok: boolean
  index_name: string
  document_id: string
  filename: string
  pages: PreviewPage[]
  timestamp: string
}

export async function previewDocument(indexName: string, documentId: string): Promise<PreviewResponse> {
  const res = await fetch(
    buildApiUrl(`/documents/${encodeURIComponent(indexName)}/${encodeURIComponent(documentId)}/preview`),
  )
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`Failed to preview document: ${res.status} ${text}`)
  }
  return res.json()
}


export async function ingestPdfs(files: File[], indexName: string, onUploadProgress?: (pct: number) => void): Promise<UploadResponse> {

  const formData = new FormData()
  for (const f of files) formData.append('files', f)

  // Client-side "progress": we approximate using fetch upload stream progress is not supported everywhere.
  // So we implement a best-effort progress by chunking into XHR below.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', buildApiUrl(`/ingest?index_name=${encodeURIComponent(indexName)}`), true)

    xhr.upload.onprogress = (evt) => {
      if (!evt.lengthComputable) return
      const pct = Math.round((evt.loaded / evt.total) * 100)
      onUploadProgress?.(pct)
    }

    xhr.onload = () => {
      try {
        const json = JSON.parse(xhr.responseText || '{}')
        if (xhr.status < 200 || xhr.status >= 300) {
          reject(new Error(json.detail || `Ingestion failed with status ${xhr.status}`))
          return
        }
        resolve(json)
      } catch {
        console.error("Raw server response:", xhr.responseText)

        reject(
          new Error(
            xhr.responseText || "The server returned an invalid response"
          )
        )
      }
    }

    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.onabort = () => reject(new Error('Upload aborted'))

    xhr.send(formData)
  })
}

