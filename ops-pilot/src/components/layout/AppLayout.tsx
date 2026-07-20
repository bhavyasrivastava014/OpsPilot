import { useEffect, useState, type ReactNode } from 'react'

import { API_BASE_URL } from '../../services/api'
import { LeftSidebar } from './LeftSidebar'

export function AppLayout({ children }: { children: ReactNode }) {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'offline'>('checking')

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    async function checkBackend() {
      try {
        const response = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal })
        if (!cancelled) {
          setBackendStatus(response.ok ? 'connected' : 'offline')
        }
      } catch {
        if (!cancelled) {
          setBackendStatus('offline')
        }
      }
    }

    void checkBackend()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [])

  const backendLabel =
    backendStatus === 'connected' ? 'Backend connected' : backendStatus === 'offline' ? 'No backend' : 'Checking backend...'

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-50">
      <div className="flex h-full w-full">
        <div className="w-[320px] shrink-0">
          <LeftSidebar />
        </div>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="shrink-0 border-b border-slate-800/70 bg-slate-950/70 backdrop-blur">
            <div className="flex items-center justify-between gap-3 px-5 py-4">
              <div>
                <div className="text-sm font-semibold text-slate-200">OpsPilot</div>
                <div className="text-xs text-slate-400">
                  AI document assistant
                </div>
              </div>
              <div className="text-xs text-slate-400">{backendLabel}</div>
            </div>
          </header>

          <main className="min-h-0 flex-1 overflow-hidden">
            <div className="h-full overflow-auto p-5">{children}</div>
          </main>
        </div>
      </div>
    </div>
  )
}



