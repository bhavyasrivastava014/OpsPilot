import { AppLayout } from '../components/layout/AppLayout'
import { ChatPanel } from '../components/chat/ChatPanel'
import { DocumentsPanel } from '../components/documents/DocumentsPanel'

export function HomePage() {
  return (
    <AppLayout>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <ChatPanel />
        </div>
        <div className="lg:col-span-5">
          <DocumentsPanel />
        </div>
      </div>
    </AppLayout>
  )
}

