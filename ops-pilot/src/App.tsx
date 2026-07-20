import { HomePage } from './pages/HomePage'
import { ToastProvider } from './components/common/toast/ToastProvider'

export default function App() {
  return (
    <ToastProvider>
      <HomePage />
    </ToastProvider>
  )
}

