import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './AuthContext.jsx'

const DEV_TOKEN_KEY = "manifest_dev_token";

if (import.meta.env.DEV) {
  const originalFetch = window.fetch;

  window.fetch = (input, init = {}) => {
    const target =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input?.url;

    if (!target?.startsWith("/api")) {
      return originalFetch(input, init);
    }

    const headers = new Headers(init.headers || {});
    const localDevToken = localStorage.getItem(DEV_TOKEN_KEY);

    if (localDevToken && !headers.has("X-Manifest-Dev-Token")) {
      headers.set("X-Manifest-Dev-Token", localDevToken);
    }

    return originalFetch(input, {
      ...init,
      headers,
    });
  };
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
