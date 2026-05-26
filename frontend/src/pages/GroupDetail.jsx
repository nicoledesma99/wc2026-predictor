import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'
import MatchPrediction from '../components/MatchPrediction'
import { getFlag } from '../utils/flags'
import { useLanguage } from '../i18n/LanguageContext'

function StandingsTable({ standings }) {
  const { t } = useLanguage()
  const hasRealGoals = standings.length > 0 && standings[0].gf != null

  const gf   = e => hasRealGoals ? e.gf  : e.xgf
  const gc   = e => hasRealGoals ? e.gc  : e.xgc
  const gd   = e => hasRealGoals ? (e.gf - e.gc) : e.xgd

  return (
    <div className="rounded-xl overflow-hidden mb-6" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
      <table className="w-full text-sm">
        <thead>
          <tr style={{ borderBottom: '1px solid #2a2a2a' }}>
            {t.groups.tableHeaders.map(h => (
              <th key={h} className="p-3 text-xs font-medium text-left first:pl-4" style={{ color: '#555' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {standings.map((entry, i) => {
            const qualifies = i < 2
            const j = entry.w + entry.d + entry.l
            const diff = gd(entry)
            return (
              <tr
                key={entry.team}
                style={{
                  borderBottom: '1px solid #1f1f1f',
                  borderLeft: `3px solid ${qualifies ? '#00ff87' : i >= standings.length - 2 ? '#ff4444' : 'transparent'}`,
                  backgroundColor: qualifies ? '#00ff870a' : i >= standings.length - 2 ? '#ff44440a' : 'transparent',
                }}
              >
                <td className="p-3 pl-4 text-xs" style={{ color: '#555' }}>{i + 1}</td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{getFlag(entry.team)}</span>
                    <span className="font-semibold text-sm" style={{ color: qualifies ? '#00ff87' : '#ccc' }}>
                      {entry.team}
                    </span>
                    {qualifies && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded font-medium hidden sm:inline"
                        style={{ backgroundColor: '#00ff8720', color: '#00ff87' }}
                      >
                        {t.groups.qualifies}
                      </span>
                    )}
                  </div>
                </td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{j}</td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{entry.w}</td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{entry.d}</td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{entry.l}</td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{gf(entry)}</td>
                <td className="p-3 text-xs" style={{ color: '#666' }}>{gc(entry)}</td>
                <td className="p-3 text-xs font-medium" style={{ color: diff > 0 ? '#00ff87' : diff < 0 ? '#ff4444' : '#666' }}>
                  {diff > 0 ? '+' : ''}{diff}
                </td>
                <td className="p-3 font-black" style={{ color: qualifies ? '#00ff87' : '#ccc' }}>{entry.pts}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function GroupDetail() {
  const { groupId } = useParams()
  const { t } = useLanguage()
  const [group, setGroup]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    api.get(`/api/groups/${groupId}`)
      .then(r => { setGroup(r.data); setLoading(false) })
      .catch(() => { setError(t.groups.groupNotFound); setLoading(false) })
  }, [groupId])

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="text-4xl animate-pulse">⚽</div>
    </div>
  )

  if (error) return (
    <div className="text-center py-24 space-y-4">
      <p style={{ color: '#ff4444' }}>{error}</p>
      <Link to="/groups" className="text-sm" style={{ color: '#00ff87' }}>{t.groups.backToGroupsLink}</Link>
    </div>
  )

  const matchdays = [...new Set(group.matches.map(m => m.matchday))].sort()

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-6">
        <Link to="/groups" className="text-sm transition-colors hover:text-white" style={{ color: '#555' }}>
          {t.groups.backToGroups}
        </Link>
        <span style={{ color: '#333' }}>/</span>
        <h1 className="text-2xl font-black" style={{ color: '#00ff87' }}>{group.group_name}</h1>
      </div>

      {/* Qualifies badges */}
      <div className="flex gap-2 flex-wrap mb-4">
        {group.qualifies.map(team => (
          <div
            key={team}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium"
            style={{ backgroundColor: '#00ff8720', color: '#00ff87', border: '1px solid #00ff8440' }}
          >
            {getFlag(team)} {team} {t.groups.qualifiesBadge}
          </div>
        ))}
      </div>

      {/* Standings */}
      <h2 className="text-sm font-bold mb-3 uppercase tracking-wide" style={{ color: '#555' }}>
        {t.groups.positions}
      </h2>
      <StandingsTable standings={group.standings} />

      {/* Matches */}
      <h2 className="text-sm font-bold mb-4 uppercase tracking-wide" style={{ color: '#555' }}>
        {t.groups.matchesTitle}
      </h2>
      {matchdays.map(md => (
        <div key={md} className="mb-4">
          <div
            className="text-xs font-bold mb-2 px-2 py-1 rounded inline-block"
            style={{ backgroundColor: '#2a2a2a', color: '#888' }}
          >
            {t.groups.matchday} {md}
          </div>
          {group.matches
            .filter(m => m.matchday === md)
            .map(match => <MatchPrediction key={match.match_id} match={match} />)
          }
        </div>
      ))}
    </div>
  )
}
