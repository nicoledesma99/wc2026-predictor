import { createContext, useContext, useState } from 'react'
import translations from './translations'

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState('es')
  const toggleLang = () => setLang(l => (l === 'es' ? 'en' : 'es'))
  const t = translations[lang]
  return (
    <LanguageContext.Provider value={{ t, lang, toggleLang }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  return useContext(LanguageContext)
}
