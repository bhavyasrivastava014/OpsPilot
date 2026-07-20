import { useId, useMemo, useState } from 'react'

type SourceCardModel = {
  display: string
  filename: string
  pageNumber: number
  confidenceScore: number
  snippet: string
  retrievedSentence: string
}

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n))
}

function formatConfidence(score: number) {
  if (!Number.isFinite(score)) return '—'
  const pct = clamp(score, 0, 1) * 100
  return `${pct.toFixed(1)}%`
}

function highlightSentence(snippet: string, sentence: string) {
  const safeSentence = sentence.trim()
  if (!safeSentence) return snippet

  const idx = snippet.toLowerCase().indexOf(safeSentence.toLowerCase())
  if (idx < 0) return snippet

  const before = snippet.slice(0, idx)
  const match = snippet.slice(idx, idx + safeSentence.length)
  const after = snippet.slice(idx + safeSentence.length)

  return (
    <>
      {before}
      <mark className="rounded border border-indigo-400/30 bg-indigo-500/20 px-1 py-[1px] text-indigo-100">
        {match}
      </mark>
      {after}
    </>
  )
}

export function SourceCard(props: { source: SourceCardModel }) {
  const { source } = props
  const [expanded, setExpanded] = useState(false)
  const regionId = useId()

  const confidenceLabel = useMemo(
    () => formatConfidence(source.confidenceScore),
    [source.confidenceScore]
  )

  return (
    <article
      className="mt-3 w-full overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/25 shadow-sm"
      aria-label="Retrieved source"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-xs font-semibold text-slate-100">{source.display}</div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
            <span className="truncate">{source.filename}</span>
            <span>• Page {source.pageNumber}</span>
            <span>• Confidence {confidenceLabel}</span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="shrink-0 rounded-full border border-slate-800/70 bg-slate-950/15 px-3 py-1.5 text-[11px] font-medium text-slate-200 transition hover:bg-slate-950/35"
          aria-expanded={expanded}
          aria-controls={regionId}
        >
          {expanded ? 'Hide snippet' : 'View snippet'}
        </button>
      </div>

      <div id={regionId} className={expanded ? 'px-4 py-3' : 'px-4 py-3'}>
        <p
          className={
            expanded
              ? 'text-sm leading-relaxed text-slate-200 whitespace-pre-wrap'
              : 'text-sm leading-relaxed text-slate-200 whitespace-pre-wrap line-clamp-3'
          }
        >
          {highlightSentence(source.snippet, source.retrievedSentence)}
        </p>
      </div>
    </article>
  )
}

