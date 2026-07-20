import { useEffect, useMemo, useRef, useState } from 'react'

export type ChatInputProps = {
  onSend: (text: string) => void
  disabled?: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    // Keep cursor position pleasant for demo.
    if (!disabled && !isFocused) textareaRef.current?.focus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const trimmed = useMemo(() => text.trim(), [text])
  const canSend = !disabled && trimmed.length > 0

  function handleSubmit() {
    if (!canSend) return
    onSend(trimmed)
    setText('')
    textareaRef.current?.focus()
  }

  return (
    <div
      className={`rounded-2xl border p-3 shadow-sm backdrop-blur transition-all duration-300
        ${disabled ? 'border-slate-800/70 bg-slate-950/25' : 'border-slate-800/80 bg-slate-950/30'}
        ${isFocused && !disabled ? 'ring-2 ring-indigo-400/15' : 'ring-0'}
      `}
    >
      <div className="flex items-start gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/15 to-cyan-500/10 ring-1 ring-white/10">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 text-indigo-200/90"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2a10 10 0 0 0-7.1 17.1c.4.4.8.7 1.3.9l1.6.7V18" />
            <path d="M12 2a10 10 0 0 1 7.1 17.1c-.4.4-.8.7-1.3.9l-1.6.7V18" />
            <path d="M8 18h8" />
            <path d="M9 22h6" />
            <path d="M9.5 9.5a2.5 2.5 0 0 1 5 0c0 1.8-2.5 2-2.5 3.5" />
            <path d="M12 16h.01" />
          </svg>
        </div>

        <div className="flex flex-1 flex-col gap-1">
          <textarea
            ref={textareaRef}
            rows={1}
            className="w-full resize-none rounded-xl border border-slate-800/80 bg-slate-950/20 px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-indigo-400/40 focus:ring-2 focus:ring-indigo-400/15 disabled:cursor-not-allowed disabled:opacity-60"
            placeholder="Ask a question about your documents..."
            value={text}
            disabled={disabled}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              // Enter = send, Shift+Enter = newline.
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit()
              }
            }}
          />

          {disabled ? (
            <div className="text-[11px] text-slate-400 transition-opacity duration-200">
              Upload is disabled while the assistant is responding (demo).
            </div>
          ) : null}
        </div>

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSend}
          className="inline-flex h-10 items-center justify-center rounded-xl bg-indigo-500/90 px-4 text-sm font-semibold text-slate-950 shadow-sm transition hover:bg-indigo-500 active:translate-y-[1px] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}


