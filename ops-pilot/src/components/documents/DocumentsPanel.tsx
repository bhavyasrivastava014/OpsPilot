import { DocumentList } from './DocumentList'

export function DocumentsPanel() {
  return (
    <section className="rounded-xl border border-slate-800/70 bg-slate-900/35 p-4 shadow-sm backdrop-blur">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-100">Documents</h2>
          <div className="mt-1 text-xs text-slate-400">Manage your PDFs</div>
        </div>
        <div className="hidden text-xs text-slate-500 sm:block">Hover a card</div>
      </div>

      <DocumentList />
    </section>
  )
}




