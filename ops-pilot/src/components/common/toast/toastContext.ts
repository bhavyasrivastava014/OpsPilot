import { createContext, useContext } from 'react'

export type Toast = {
  id: string
  title: string
  message?: string
  tone?: 'success' | 'error' | 'info'
  durationMs?: number
}

export type ToastContextValue = {
  push: (toast: Omit<Toast, 'id'>) => void
}

export const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
