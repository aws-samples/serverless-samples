import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import I18nProvider from '@cloudscape-design/components/i18n'
// Import all locales
import messages from '@cloudscape-design/components/i18n/messages/all.all';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider messages={[messages]}>
      <App />
    </I18nProvider>
  </React.StrictMode>,
)
