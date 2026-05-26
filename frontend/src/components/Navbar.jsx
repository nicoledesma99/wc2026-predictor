import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'

export default function Navbar() {
  const { pathname } = useLocation()
  const { t, lang, toggleLang } = useLanguage()
  const [open, setOpen] = useState(false)

  const LINKS = [
    { to: '/',            icon: '🏠', label: t.nav.home       },
    { to: '/groups',      icon: '🏆', label: t.nav.groups     },
    { to: '/predictions', icon: '⚽', label: t.nav.predictions },
    { to: '/favorites',   icon: '⭐', label: t.nav.favorites  },
    { to: '/model',       icon: '🤖', label: t.nav.model      },
  ]

  const isActive = (to) =>
    pathname === to || (to !== '/' && pathname.startsWith(to))

  return (
    <nav style={{ backgroundColor: '#111', borderBottom: '1px solid #2a2a2a', position: 'sticky', top: 0, zIndex: 50 }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 24px' }}>
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link
            to="/"
            className="font-black text-xl tracking-tight shrink-0"
            style={{ color: '#00ff87' }}
            onClick={() => setOpen(false)}
          >
            ⚽ WC2026
          </Link>

          {/* Desktop links + lang toggle */}
          <div className="hidden md:flex items-center gap-1">
            {LINKS.map(({ to, icon, label }) => {
              const active = isActive(to)
              return (
                <Link
                  key={to}
                  to={to}
                  className="relative px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap"
                  style={{
                    color: active ? '#00ff87' : '#888',
                    backgroundColor: active ? '#00ff8715' : 'transparent',
                    transition: 'color 0.15s ease, background-color 0.15s ease',
                  }}
                >
                  <span className="mr-1">{icon}</span>{label}
                  {active && (
                    <span
                      className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full"
                      style={{ backgroundColor: '#00ff87' }}
                    />
                  )}
                </Link>
              )
            })}

            {/* Language toggle */}
            <LangToggle lang={lang} toggleLang={toggleLang} />
          </div>

          {/* Mobile: lang toggle + hamburger */}
          <div className="flex md:hidden items-center gap-2">
            <LangToggle lang={lang} toggleLang={toggleLang} />
            <button
              className="flex flex-col justify-center gap-1 w-8 h-8 p-1"
              onClick={() => setOpen(v => !v)}
              aria-label="Menú"
            >
              <span className="block h-0.5 rounded-full" style={{ backgroundColor: '#aaa', transition: 'transform 0.2s', transform: open ? 'rotate(45deg) translateY(6px)' : 'none' }} />
              <span className="block h-0.5 rounded-full" style={{ backgroundColor: '#aaa', transition: 'opacity 0.2s', opacity: open ? 0 : 1 }} />
              <span className="block h-0.5 rounded-full" style={{ backgroundColor: '#aaa', transition: 'transform 0.2s', transform: open ? 'rotate(-45deg) translateY(-6px)' : 'none' }} />
            </button>
          </div>
        </div>

        {/* Mobile dropdown */}
        {open && (
          <div className="md:hidden pb-3 space-y-1" style={{ borderTop: '1px solid #1a1a1a' }}>
            {LINKS.map(({ to, icon, label }) => {
              const active = isActive(to)
              return (
                <Link
                  key={to}
                  to={to}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium"
                  style={{
                    color: active ? '#00ff87' : '#888',
                    backgroundColor: active ? '#00ff8715' : 'transparent',
                    borderLeft: `3px solid ${active ? '#00ff87' : 'transparent'}`,
                    transition: 'all 0.15s ease',
                  }}
                  onClick={() => setOpen(false)}
                >
                  <span>{icon}</span><span>{label}</span>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </nav>
  )
}

function LangToggle({ lang, toggleLang }) {
  return (
    <div
      className="flex items-center rounded-lg overflow-hidden text-xs font-bold cursor-pointer"
      style={{ border: '1px solid #2a2a2a' }}
      onClick={toggleLang}
    >
      <span
        className="px-2 py-1.5"
        style={{
          backgroundColor: lang === 'es' ? '#00ff8718' : 'transparent',
          color:           lang === 'es' ? '#00ff87'   : '#555',
          transition: 'all 0.15s ease',
        }}
      >
        🇪🇸 ES
      </span>
      <span style={{ color: '#2a2a2a' }}>|</span>
      <span
        className="px-2 py-1.5"
        style={{
          backgroundColor: lang === 'en' ? '#00ff8718' : 'transparent',
          color:           lang === 'en' ? '#00ff87'   : '#555',
          transition: 'all 0.15s ease',
        }}
      >
        EN 🇬🇧
      </span>
    </div>
  )
}
