import { useState, useEffect, useMemo } from 'react'
import api from '../api/client'
import MatchPrediction from '../components/MatchPrediction'
import { useLanguage } from '../i18n/LanguageContext'

const GROUPS = ['A','B','C','D','E','F','G','H','I','J','K','L']
const JORNADAS = ['all', '1', '2', '3']

export default function Predictions() {
  const { t } = useLanguage()
  const [predictions, setPredictions]   = useState([])
  const [loading, setLoading]           = useState(true)
  const [selectedGroup, setSelectedGroup] = useState('')
  const [sortBy, setSortBy]             = useState('date')
  const [selectedTeam, setSelectedTeam] = useState('')
  const [jornada, setJornada]           = useState('all')
  const [highConfOnly, setHighConfOnly] = useState(false)

  useEffect(() => {
    api.get('/api/predictions')
      .then(r => { setPredictions(r.data.predictions); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  // Unique team list for dropdown
  const teams = useMemo(() => {
    const set = new Set()
    predictions.forEach(m => { set.add(m.home_team); set.add(m.away_team) })
    return [...set].sort()
  }, [predictions])

  const filtered = useMemo(() => {
    let res = predictions.filter(m => {
      const matchesTeam  = !selectedTeam || m.home_team === selectedTeam || m.away_team === selectedTeam
      const matchesGroup = !selectedGroup || m.group === `Group ${selectedGroup}`
      const matchesJ     = jornada === 'all' || m.matchday === parseInt(jornada)
      const maxProb      = Math.max(m.prob_home_win, m.prob_draw, m.prob_away_win)
      const matchesConf  = !highConfOnly || maxProb >= 0.60
      return matchesTeam && matchesGroup && matchesJ && matchesConf
    })
    if (sortBy === 'date')  return [...res].sort((a, b) => a.date.localeCompare(b.date))
    if (sortBy === 'group') return [...res].sort((a, b) => a.group.localeCompare(b.group) || a.matchday - b.matchday)
    return res
  }, [predictions, selectedTeam, selectedGroup, jornada, highConfOnly, sortBy])

  const selectStyle = {
    backgroundColor: '#1a1a1a',
    border: '1px solid #2a2a2a',
    color: '#ccc',
    borderRadius: '8px',
    padding: '8px 12px',
    fontSize: '14px',
    outline: 'none',
  }

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="text-4xl animate-pulse">⚽</div>
    </div>
  )

  return (
    <div>
      {/* Title */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-black" style={{ color: '#00ff87' }}>{t.predictions.title}</h1>
          <p className="text-xs mt-0.5" style={{ color: '#555' }}>{t.predictions.subtitle}</p>
        </div>
      </div>

      {/* ── Sticky filter bar ── */}
      <div
        className="sticky z-10 rounded-xl p-3 mb-4 space-y-3"
        style={{ top: '60px', backgroundColor: '#111', border: '1px solid #2a2a2a', backdropFilter: 'blur(8px)' }}
      >
        {/* Row 1: team dropdown + group + sort */}
        <div className="flex flex-wrap gap-2">
          {/* Team dropdown */}
          <select
            value={selectedTeam}
            onChange={e => setSelectedTeam(e.target.value)}
            style={{ ...selectStyle, flex: '1 1 160px' }}
          >
            <option value="">{t.predictions.allTeams}</option>
            {teams.map(team => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>

          {/* Group filter */}
          <select value={selectedGroup} onChange={e => setSelectedGroup(e.target.value)} style={selectStyle}>
            <option value="">{t.predictions.allGroups}</option>
            {GROUPS.map(g => <option key={g} value={g}>{t.common.group} {g}</option>)}
          </select>

          {/* Sort */}
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={selectStyle}>
            <option value="date">{t.predictions.byDate}</option>
            <option value="group">{t.predictions.byGroup}</option>
          </select>
        </div>

        {/* Row 2: jornada toggles + high-conf + counter */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1">
            {JORNADAS.map(j => (
              <button
                key={j}
                onClick={() => setJornada(j)}
                className="px-3 py-1 rounded-lg text-xs font-bold"
                style={{
                  backgroundColor: jornada === j ? '#00ff87' : '#1a1a1a',
                  color:           jornada === j ? '#000'    : '#666',
                  border:          `1px solid ${jornada === j ? '#00ff87' : '#2a2a2a'}`,
                  transition: 'all 0.15s ease',
                }}
              >
                {j === 'all' ? t.predictions.all : `J${j}`}
              </button>
            ))}
          </div>

          <button
            onClick={() => setHighConfOnly(v => !v)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold"
            style={{
              backgroundColor: highConfOnly ? '#00ff8718' : '#1a1a1a',
              color:           highConfOnly ? '#00ff87'   : '#666',
              border:          `1px solid ${highConfOnly ? '#00ff8840' : '#2a2a2a'}`,
              transition: 'all 0.15s ease',
            }}
          >
            🔥 {t.predictions.highConf}
          </button>

          <span className="ml-auto text-xs" style={{ color: '#555' }}>
            {t.predictions.showing}{' '}
            <span style={{ color: '#ccc', fontWeight: 700 }}>{filtered.length}</span>
            {' '}{t.predictions.of} {predictions.length} {t.predictions.matches}
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mb-3">
        {[['#00ff87', t.predictions.homeWin], ['#ffaa00', t.predictions.draw], ['#ff4444', t.predictions.awayWin]].map(([color, label]) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ backgroundColor: color }} />
            <span className="text-xs" style={{ color: '#555' }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Match list */}
      <div>
        {filtered.length === 0 ? (
          <div className="text-center py-16" style={{ color: '#555' }}>
            <div className="text-4xl mb-3">🔍</div>
            <p className="text-sm">{t.predictions.noResults}</p>
            <p className="text-xs mt-1" style={{ color: '#444' }}>{t.predictions.noResultsHint}</p>
          </div>
        ) : (
          filtered.map(match => (
            <MatchPrediction
              key={match.match_id || `${match.home_team}-${match.away_team}`}
              match={match}
            />
          ))
        )}
      </div>
    </div>
  )
}
