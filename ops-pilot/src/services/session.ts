const INDEX_STORAGE_KEY = 'opspilot-index-name'

export function getIndexName(): string {
  const existing = window.localStorage.getItem(INDEX_STORAGE_KEY)
  if (existing && /^[A-Za-z0-9_-]{1,100}$/.test(existing)) return existing

  const indexName = `session_${crypto.randomUUID().replaceAll('-', '')}`
  window.localStorage.setItem(INDEX_STORAGE_KEY, indexName)
  return indexName
}

export function notifyDocumentsChanged(): void {
  window.dispatchEvent(new Event('opspilot-documents-changed'))
}
