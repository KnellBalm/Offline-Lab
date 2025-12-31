import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { PostHogProvider } from 'posthog-js/react'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import './styles/theme.css'
import './index.css'
import App from './App.tsx'

const posthogOptions = {
  api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
}

const posthogKey = import.meta.env.VITE_POSTHOG_KEY || ''

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        {posthogKey ? (
          <PostHogProvider apiKey={posthogKey} options={posthogOptions}>
            <App />
          </PostHogProvider>
        ) : (
          <App />
        )}
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)

