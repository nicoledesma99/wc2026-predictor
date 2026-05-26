import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { getFlag } from '../utils/flags'
import TeamBadge from '../components/TeamBadge'
import ProbabilityBar from '../components/ProbabilityBar'
import { useLanguage } from '../i18n/LanguageContext'

const NAV_CARDS = [
  { to: '/groups',      icon: '🏆', key: 'groups',      desc: { es: '12 grupos · Tabla predicha',        en: '12 groups · Predicted standings'  } },
  { to: '/predictions', icon: '⚽', key: 'predictions', desc: { es: '72 partidos · Probabilidades',       en: '72 matches · Probabilities'        } },
  { to: '/favorites',   icon: '⭐', key: 'favorites',   desc: { es: 'Top 10 · Mayor probabilidad',        en: 'Top 10 · Highest probability'      } },
  { to: '/model',       icon: '🤖', key: 'model',       desc: { es: 'Accuracy · Features · CV Score',     en: 'Accuracy · Features · CV Score'    } },
]

function StatCard({ value, label, color = '#00ff87' }) {
  return (
    <div className="rounded-xl p-4 text-center" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
      <div className="text-2xl font-black mb-1 leading-tight" style={{ color }}>{value}</div>
      <div className="text-xs" style={{ color: '#666' }}>{label}</div>
    </div>
  )
}

const fmtDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00Z')
  return d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function Home() {
  const { t, lang } = useLanguage()
  const [modelInfo, setModelInfo]     = useState(null)
  const [favorites, setFavorites]     = useState([])
  const [predictions, setPredictions] = useState([])

  useEffect(() => {
    api.get('/api/model-info').then(r => setModelInfo(r.data)).catch(() => {})
    api.get('/api/favorites').then(r => setFavorites(r.data.favorites)).catch(() => {})
    api.get('/api/predictions').then(r => setPredictions(r.data.predictions)).catch(() => {})
  }, [])

  const nextMatch = predictions.length
    ? [...predictions].sort((a, b) => a.date.localeCompare(b.date))[0]
    : null

  const highConfCount = predictions.filter(m =>
    Math.max(m.prob_home_win, m.prob_draw, m.prob_away_win) >= 0.60
  ).length
  const homeWins = predictions.filter(m => m.predicted_result_label === 'home_win').length
  const draws    = predictions.filter(m => m.predicted_result_label === 'draw').length
  const awayWins = predictions.filter(m => m.predicted_result_label === 'away_win').length

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center pt-10 pb-4">
        <div className="text-5xl mb-3">⚽</div>
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-2" style={{ color: '#00ff87' }}>
          {t.home.title}
        </h1>
        <p className="text-2xl font-bold text-white mb-3">{t.home.subtitle}</p>
        <p className="text-sm max-w-md mx-auto" style={{ color: '#666' }}>{t.home.desc}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard value="48" label={t.home.teams} />
        <StatCard value="72" label={t.home.matches} />
        <StatCard
          value={modelInfo ? `${(modelInfo.accuracy * 100).toFixed(1)}%` : '…'}
          label={t.home.accuracy}
          color="#ffaa00"
        />
        <StatCard value="Poisson" label={t.home.goalsModel} color="#aa88ff" />
      </div>

      {/* Próximo partido */}
      {nextMatch && (
        <div>
          <h2 className="text-sm font-black mb-3 uppercase tracking-wide" style={{ color: '#555' }}>
            {t.home.nextMatch}
          </h2>
          <div className="rounded-xl p-4" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
            <div className="flex justify-between items-center mb-3">
              <span className="text-xs font-medium" style={{ color: '#00ff87' }}>{fmtDate(nextMatch.date)}</span>
              <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: '#2a2a2a', color: '#888' }}>
                {nextMatch.group} · J{nextMatch.matchday}
              </span>
            </div>
            <div className="flex items-center justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getFlag(nextMatch.home_team)}</span>
                <div>
                  <div className="font-bold text-sm" style={{ color: nextMatch.predicted_result_label === 'home_win' ? '#00ff87' : '#aaa' }}>
                    {nextMatch.home_team}
                  </div>
                  {nextMatch.home_goals != null && (
                    <div className="text-xl font-black" style={{ color: nextMatch.predicted_result_label === 'home_win' ? '#00ff87' : '#555' }}>
                      {nextMatch.home_goals}
                    </div>
                  )}
                </div>
              </div>
              <div className="text-center">
                {nextMatch.home_goals != null
                  ? <div className="text-xl font-black" style={{ color: '#444' }}>-</div>
                  : <div className="text-sm font-bold" style={{ color: '#333' }}>{t.common.vs}</div>
                }
              </div>
              <div className="flex items-center gap-2 flex-row-reverse">
                <span className="text-2xl">{getFlag(nextMatch.away_team)}</span>
                <div className="text-right">
                  <div className="font-bold text-sm" style={{ color: nextMatch.predicted_result_label === 'away_win' ? '#00ff87' : '#aaa' }}>
                    {nextMatch.away_team}
                  </div>
                  {nextMatch.away_goals != null && (
                    <div className="text-xl font-black" style={{ color: nextMatch.predicted_result_label === 'away_win' ? '#00ff87' : '#555' }}>
                      {nextMatch.away_goals}
                    </div>
                  )}
                </div>
              </div>
            </div>
            <ProbabilityBar
              probHome={nextMatch.prob_home_win}
              probDraw={nextMatch.prob_draw}
              probAway={nextMatch.prob_away_win}
              homeTeam={nextMatch.home_team}
              awayTeam={nextMatch.away_team}
            />
          </div>
        </div>
      )}

      {/* Distribution */}
      {predictions.length > 0 && (
        <div>
          <h2 className="text-sm font-black mb-3 uppercase tracking-wide" style={{ color: '#555' }}>
            {t.home.distribution}
          </h2>
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-xl p-3 text-center" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
              <div className="text-xl font-black" style={{ color: '#00ff87' }}>{homeWins}</div>
              <div className="text-xs mt-0.5" style={{ color: '#666' }}>{t.home.homeWins}</div>
            </div>
            <div className="rounded-xl p-3 text-center" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
              <div className="text-xl font-black" style={{ color: '#ffaa00' }}>{draws}</div>
              <div className="text-xs mt-0.5" style={{ color: '#666' }}>{t.home.draws}</div>
            </div>
            <div className="rounded-xl p-3 text-center" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
              <div className="text-xl font-black" style={{ color: '#ff4444' }}>{awayWins}</div>
              <div className="text-xs mt-0.5" style={{ color: '#666' }}>{t.home.awayWins}</div>
            </div>
          </div>
          {highConfCount > 0 && (
            <p className="text-xs mt-2 text-center" style={{ color: '#555' }}>
              <span style={{ color: '#00ff87', fontWeight: 700 }}>{highConfCount}</span> {t.home.highConfNote}
            </p>
          )}
        </div>
      )}

      {/* Top 5 */}
      {favorites.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-black flex items-center gap-2">
              <span style={{ color: '#00ff87' }}>⭐</span> {t.home.topFavorites}
            </h2>
            <Link to="/favorites" className="text-xs" style={{ color: '#555' }}>{t.home.viewAll}</Link>
          </div>
          <div className="space-y-2">
            {favorites.slice(0, 5).map((fav, i) => (
              <div
                key={fav.team}
                className="rounded-xl p-3"
                style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', transition: 'border-color 0.2s ease' }}
                onMouseEnter={e => e.currentTarget.style.borderColor = '#3a3a3a'}
                onMouseLeave={e => e.currentTarget.style.borderColor = '#2a2a2a'}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-black w-6 text-center" style={{ color: i === 0 ? '#00ff87' : '#555' }}>
                      {i + 1}
                    </span>
                    <TeamBadge team={fav.team} ranking={fav.ranking} highlight={i === 0} />
                  </div>
                  <div className="font-black text-lg" style={{ color: '#00ff87' }}>
                    {Math.round(fav.avg_win_prob * 100)}%
                  </div>
                </div>
                <ProbabilityBar
                  probHome={fav.avg_win_prob}
                  probDraw={Math.min(0.22, 1 - fav.avg_win_prob - 0.1)}
                  probAway={Math.max(0.05, 1 - fav.avg_win_prob - Math.min(0.22, 1 - fav.avg_win_prob - 0.1))}
                  compact
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Nav cards */}
      <div>
        <h2 className="text-lg font-black mb-4">{t.home.explore}</h2>
        <div className="grid grid-cols-2 gap-3">
          {NAV_CARDS.map(({ to, icon, key, desc }) => (
            <Link
              key={to}
              to={to}
              className="rounded-xl p-4"
              style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', transition: 'all 0.15s ease' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = '#3a3a3a'; e.currentTarget.style.transform = 'scale(1.02)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a2a'; e.currentTarget.style.transform = 'scale(1)' }}
            >
              <div className="text-2xl mb-2">{icon}</div>
              <div className="font-bold text-sm text-white mb-1">{t.nav[key]}</div>
              <div className="text-xs" style={{ color: '#555' }}>{desc[lang]}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* Footer */}
      {modelInfo && (
        <p className="text-center text-xs pb-6" style={{ color: '#333' }}>
          {modelInfo.model_name} · CV {(modelInfo.cv_mean * 100).toFixed(1)}% ± {(modelInfo.cv_std * 100).toFixed(1)}% · {modelInfo.training_rows?.toLocaleString()} {t.home.footer}
        </p>
      )}
    </div>
  )
}
