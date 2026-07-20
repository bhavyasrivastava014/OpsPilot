import type { ReactNode } from 'react'
import { useMemo, useState } from 'react'
import { ToastContext, type Toast, type ToastContextValue } from './toastContext'

function makeId() {
  return `toast_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const value = useMemo<ToastContextValue>(
    () => ({
      push: (t) => {
        const toast: Toast = {
          id: makeId(),
          tone: 'info',
          durationMs: 4000,
          ...t,
        }
        setToasts((prev) => [...prev, toast])

        const timeout = window.setTimeout(() => {
          setToasts((prev) => prev.filter((x) => x.id !== toast.id))
        }, toast.durationMs)

        return () => window.clearTimeout(timeout)
      },
    }),
    [],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="bb-toast-region"
        aria-live="polite"
        role="status"
        aria-relevant="additions"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`bb-toast bb-toast--${t.tone ?? 'info'}`}
            role="status"
          >
            <div className="bb-toast__title">{t.title}</div>
            {t.message ? <div className="bb-toast__message">{t.message}</div> : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}


