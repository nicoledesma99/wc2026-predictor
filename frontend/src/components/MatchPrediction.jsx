import ProbabilityBar from './ProbabilityBar'
import { getFlag } from '../utils/flags'
import { useLanguage } from '../i18n/LanguageContext'

const fmtDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00Z')
  return d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function MatchPrediction({ match }) {
  const { t } = useLanguage()
  const {
    home_team, away_team,
    prob_home_win, prob_draw, prob_away_win,
    date, matchday, predicted_result_label, group,
    home_goals, away_goals,
  } = match

  const homeWins  = predicted_result_label === 'home_win'
  const awayWins  = predicted_result_label === 'away_win'
  const isDraw    = predicted_result_label === 'draw'
  const hasScore  = home_goals != null && away_goals != null

  const maxProb   = Math.max(prob_home_win, prob_draw, prob_away_win)
  const minProb   = Math.min(prob_home_win, prob_draw, prob_away_win)
  const isHighConf = maxProb >= 0.60
  const isTight    = (maxProb - minProb) < 0.15

  const teamColor = (role) => {
    if (isDraw) return '#ffaa00'
    if (role === 'home' && homeWins) return '#00ff87'
    if (role === 'away' && awayWins) return '#00ff87'
    return '#666'
  }

  return (
    <div
      className="rounded-xl p-4 mb-2"
      style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', transition: 'border-color 0.2s ease' }}
      onMouseEnter={e => e.currentTarget.style.borderColor = '#3a3a3a'}
      onMouseLeave={e => e.currentTarget.style.borderColor = '#2a2a2a'}
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-xs" style={{ color: '#555' }}>{fmtDate(date)}</span>
        <div className="flex items-center gap-2 flex-wrap justify-end">
          {isHighConf && (
            <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: '#00ff8718', color: '#00ff87' }}>
              🔥 {t.predictions.highConfBadge}
            </span>
          )}
          {isTight && !isHighConf && (
            <span className="text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: '#ffaa0018', color: '#ffaa00' }}>
              ⚖️ {t.predictions.evenBadge}
            </span>
          )}
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: '#2a2a2a', color: '#888' }}>
            {group} · J{matchday}
          </span>
        </div>
      </div>

      {/* Teams + score */}
      <div className="flex items-center justify-between gap-3 mb-4">
        {/* Home */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-2xl shrink-0">{getFlag(home_team)}</span>
          <div className="min-w-0">
            <div className="font-bold text-sm leading-tight truncate" style={{ color: teamColor('home'), transition: 'color 0.2s ease' }}>
              {home_team}
            </div>
            {hasScore && (
              <div className="text-2xl font-black leading-none mt-0.5" style={{ color: teamColor('home') }}>
                {home_goals}
              </div>
            )}
          </div>
        </div>

        {/* Center */}
        <div className="flex flex-col items-center shrink-0 px-1">
          {hasScore
            ? <div className="text-xl font-black" style={{ color: isDraw ? '#ffaa00' : '#555' }}>-</div>
            : <div className="text-sm font-bold" style={{ color: '#333' }}>{t.common.vs}</div>
          }
          {isDraw && hasScore && (
            <div className="text-[10px] font-bold mt-0.5" style={{ color: '#ffaa00' }}>{t.common.draw.toUpperCase()}</div>
          )}
        </div>

        {/* Away */}
        <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
          <div className="min-w-0 text-right">
            <div className="font-bold text-sm leading-tight truncate" style={{ color: teamColor('away'), transition: 'color 0.2s ease' }}>
              {away_team}
            </div>
            {hasScore && (
              <div className="text-2xl font-black leading-none mt-0.5" style={{ color: teamColor('away') }}>
                {away_goals}
              </div>
            )}
          </div>
          <span className="text-2xl shrink-0">{getFlag(away_team)}</span>
        </div>
      </div>

      <ProbabilityBar
        probHome={prob_home_win}
        probDraw={prob_draw}
        probAway={prob_away_win}
        homeTeam={home_team}
        awayTeam={away_team}
      />
    </div>
  )
}
