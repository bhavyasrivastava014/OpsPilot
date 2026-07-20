import { useEffect, useMemo, useRef, useState } from 'react'

import { postChat, type ChatSource as ApiChatSource } from '../../services/chatApi'
import { getIndexName } from '../../services/session'
import { ChatInput } from './ChatInput'
import { SourceCard } from './SourceCard'
import { Skeleton } from '../common/Skeleton'
import { useToast } from '../common/toast/toastContext'


type ChatRole = 'user' | 'assistant'

type SourceCardModel = {
  display: string
  filename: string
  pageNumber: number
  confidenceScore: number
  snippet: string
  retrievedSentence: string
}

type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: number
  sources?: SourceCardModel[]
}

type TypingState =
  | { status: 'idle' }
  | {
      status: 'loading'
      assistantMessageId: string
    }

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function makeId(prefix: string) {
  return `${prefix}_${crypto.randomUUID()}`
}

function currentTime() {
  return Date.now()
}

function apiSourceToSourceCardModel(src: ApiChatSource): SourceCardModel {
  return {
    display: src.filename ?? 'Unknown document',
    filename: src.filename ?? 'Unknown file',
    pageNumber: src.page ?? 0,
    confidenceScore: src.similarity_score,
    snippet: src.text,
    retrievedSentence: src.text,
  }
}

function AssistantTypingEllipsis() {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 h-9 w-9 shrink-0 rounded-xl bg-indigo-500/10 ring-1 ring-indigo-400/20 flex items-center justify-center">
        <span className="text-indigo-200">AI</span>
      </div>
      <div className="min-w-0">
        <div className="rounded-2xl border border-slate-800/70 bg-slate-950/30 px-4 py-3 text-sm text-slate-200">
          <div className="flex items-center gap-2" aria-label="Assistant is typing" role="status">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyChatState({ onQuickPrompt }: { onQuickPrompt: (p: string) => void }) {
  const prompts = ['Summarize obligations', 'Extract payment terms', 'List risks and penalties']
  return (
    <div className="flex h-full items-center justify-center">
      <div className="w-full max-w-xl rounded-2xl border border-slate-800/70 bg-slate-950/25 p-6">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 h-10 w-10 rounded-xl bg-indigo-500/10 ring-1 ring-indigo-400/20 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-200" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold text-slate-100">Ask your documents</div>
            <div className="mt-1 text-xs text-slate-400">
              Select a quick prompt below or type a question. Results will be grounded using your uploaded PDFs.
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {prompts.map((p) => (
                <button
                  key={p}
                  type="button"
                  className="rounded-full border border-slate-800/70 bg-slate-950/20 px-3 py-1.5 text-[11px] font-medium text-slate-200 hover:bg-slate-950/35"
                  onClick={() => onQuickPrompt(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

type Props = {
  onError?: (message: string) => void
}

export function ChatPanel({ onError }: Props) {
  const { push } = useToast()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [typing, setTyping] = useState<TypingState>({ status: 'idle' })
  const [sessionId, setSessionId] = useState<string | undefined>(undefined)


  const endRef = useRef<HTMLDivElement | null>(null)

  const assistantLoading = typing.status === 'loading'

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, assistantLoading])

  async function handleSend(userText: string) {
    if (typing.status !== 'idle') return

    const now = currentTime()
    const userMessage: ChatMessage = {
      id: makeId('user'),
      role: 'user',
      content: userText,
      createdAt: now,
    }

    const assistantMessageId = makeId('assistant')
    const assistantPlaceholder: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '…',
      createdAt: currentTime(),
    }

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
    setTyping({ status: 'loading', assistantMessageId })

    try {
      const resp = await postChat({
        question: userText,
        sessionId,
        indexName: getIndexName(),
        topK: 4,
      })

      setSessionId(resp.session_id)

      const answer = resp.answer ?? ''
      const sources = (resp.sources ?? []).map(apiSourceToSourceCardModel)

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                content: answer,
                sources: sources.length ? sources : undefined,
              }
            : m
        )
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed'

      let friendly = 'Sorry—could not get a response from the chat service. Please try again.'

      if (
        msg.includes('actively refused') ||
        msg.includes('Failed to establish a new connection') ||
        msg.includes('Connection refused') ||
        msg.includes('11434') ||
        msg.includes('Max retries exceeded')
      ) {
        friendly = 'Chat service cannot reach the local Ollama server. Start Ollama or update the backend OLLAMA_URL.'
      }

      onError?.(friendly)
      push({ title: 'Chat error', message: friendly, tone: 'error' })

      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                content: friendly,
                sources: undefined,
              }
            : m
        )
      )
    } finally {
      setTyping({ status: 'idle' })
    }
  }

  const quickPrompts = useMemo(
    () => ['Summarize obligations', 'Extract payment terms', 'List risks and penalties'],
    []
  )

  return (
    <section className="flex h-full min-h-[520px] flex-col rounded-2xl border border-slate-800/70 bg-slate-950/30 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-slate-800/70 px-5 py-4">

        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-100">Chat</div>
          <div className="truncate text-xs text-slate-400">Connected to backend • retrieval + Ollama</div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400/90 shadow-[0_0_20px_rgba(52,211,153,0.6)]" />
          <span className="text-xs text-slate-400">Online</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 px-5 py-4">
        <div className="h-full overflow-auto rounded-xl border border-slate-800/60 bg-slate-900/20 p-4">
          <div className="flex h-full flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => void handleSend(p)}
                  disabled={typing.status !== 'idle'}
                  className="rounded-full border border-slate-800/70 bg-slate-950/20 px-3 py-1.5 text-[11px] font-medium text-slate-200 hover:bg-slate-950/35 disabled:opacity-50"
                >
                  {p}
                </button>
              ))}
            </div>

            {messages.length === 0 ? (
              <EmptyChatState onQuickPrompt={(p) => void handleSend(p)} />
            ) : (
              <div className="space-y-3" role="log" aria-live="polite" aria-relevant="additions">
                {messages.map((m) => (
                  <MessageBubble key={m.id} msg={m} />
                ))}

                {assistantLoading ? (
                  <div className="animate-in fade-in duration-150">
                    <AssistantTypingEllipsis />
                    <div className="mt-2">
                      <Skeleton className="h-10 w-full" aria-hidden="true" />
                    </div>
                  </div>
                ) : null}

                <div ref={endRef} />
              </div>
            )}
          </div>
        </div>
      </div>


      <div className="shrink-0 border-t border-slate-800/70 px-5 py-4">
        <ChatInput onSend={(t) => void handleSend(t)} disabled={typing.status !== 'idle'} />
      </div>
    </section>
  )
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'

  return (
    <div
      className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in duration-150`}
    >

      {!isUser ? (
        <div className="mt-0.5 h-9 w-9 shrink-0 rounded-xl bg-indigo-500/10 ring-1 ring-indigo-400/20 flex items-center justify-center">
          <span className="text-indigo-200">AI</span>
        </div>
      ) : null}

      <div className={`min-w-0 max-w-[78%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm shadow-sm ring-1 ring-slate-800/60 whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-indigo-500/15 text-slate-100 ring-indigo-400/20'
              : 'bg-slate-950/30 text-slate-200'
          }`}
        >
          {msg.content}
        </div>

        {!isUser && msg.sources && msg.sources.length ? (
          <div className="mt-3 space-y-0">
            {msg.sources.map((s, idx) => (
              <SourceCard key={`${msg.id}_src_${idx}`} source={s} />
            ))}
          </div>
        ) : null}

        <div className={`mt-1 text-[11px] ${isUser ? 'text-slate-400 text-right' : 'text-slate-500'}`}>
          {formatTime(msg.createdAt)}
        </div>
      </div>

      {isUser ? (
        <div className="mt-0.5 h-9 w-9 shrink-0 rounded-xl bg-slate-100/5 ring-1 ring-slate-200/10 flex items-center justify-center">
          <span className="text-slate-200">You</span>
        </div>
      ) : null}
    </div>
  )
}

// Kept from previous implementation: typing dot animation
const _style = `
  .typing-dot {
    width: 6px;
    height: 6px;
    border-radius: 9999px;
    background: rgba(148, 163, 184, 0.95);
    display: inline-block;
    animation: bbTyping 1.2s infinite ease-in-out;
  }
  .typing-dot:nth-child(2){ animation-delay: 0.15s; }
  .typing-dot:nth-child(3){ animation-delay: 0.30s; }
  @keyframes bbTyping {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.55; }
    40% { transform: translateY(-4px); opacity: 1; }
  }
`

const injectedKey = '__bb_typing_style__'
if (typeof document !== 'undefined' && !document.getElementById(injectedKey)) {
  const styleEl = document.createElement('style')
  styleEl.id = injectedKey
  styleEl.textContent = _style
  document.head.appendChild(styleEl)
}

