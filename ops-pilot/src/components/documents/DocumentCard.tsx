

export type DocumentStatus = 'Ready' | 'Processing' | 'Error'

export type DocumentCardModel = {
  id: string
  filename: string
  pages: number
  status: DocumentStatus
}

function PdfIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
      <path d="M8 13h8" />
      <path d="M8 17h6" />
      <path d="M8 9h4" />
    </svg>
  )
}

export function DocumentCard({
  doc,
  onPreview,
  onDelete,
}: {
  doc: DocumentCardModel
  onPreview?: (doc: DocumentCardModel) => void
  onDelete?: (doc: DocumentCardModel) => void
}) {
  const statusStyles: Record<DocumentStatus, string> = {
    Ready:
      'bg-emerald-500/10 text-emerald-200 ring-1 ring-emerald-500/20',
    Processing:
      'bg-amber-500/10 text-amber-200 ring-1 ring-amber-500/20',
    Error: 'bg-rose-500/10 text-rose-200 ring-1 ring-rose-500/20',
  }

  return (
    <article
      className="group relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-950/30 p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-700/90 hover:bg-slate-950/45 hover:shadow-[0_0_0_1px_rgba(148,163,184,0.18),0_12px_40px_rgba(2,6,23,0.6)]"
    >
      {/* hover shine */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-20 -top-20 h-40 w-40 -rotate-12 bg-gradient-to-tr from-indigo-500/0 via-indigo-500/20 to-cyan-500/0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      />

      <div className="relative flex items-start gap-4">
        <div
          className={
            'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-900/60 ring-1 ring-slate-800/70 transition-colors group-hover:bg-slate-900/75'
          }
        >
          <PdfIcon className="h-6 w-6 text-indigo-200" />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="truncate text-sm font-semibold text-slate-100">
                {doc.filename}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {doc.pages} page{doc.pages === 1 ? '' : 's'}
              </div>
            </div>

            <div className="flex shrink-0 items-center">
              <span
                className={
                  `inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium ${statusStyles[doc.status]}`
                }
              >
                {doc.status}
              </span>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2 opacity-0 transition-all duration-300 group-hover:opacity-100">
            <button
              type="button"
              onClick={() => onPreview?.(doc)}
              className={
                'rounded-xl bg-indigo-500/15 px-3 py-2 text-xs font-semibold text-indigo-100 ring-1 ring-indigo-500/20 transition hover:bg-indigo-500/25 hover:ring-indigo-500/30'
              }
            >
              Preview
            </button>
            <button
              type="button"
              onClick={() => onDelete?.(doc)}
              className={
                'rounded-xl bg-rose-500/10 px-3 py-2 text-xs font-semibold text-rose-100 ring-1 ring-rose-500/20 transition hover:bg-rose-500/20 hover:ring-rose-500/30'
              }
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-indigo-400/30 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      />
    </article>
  )
}

