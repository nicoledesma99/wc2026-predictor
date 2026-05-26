import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getFlag } from '../utils/flags'
import { useLanguage } from '../i18n/LanguageContext'

export default function GroupCard({ group }) {
  const navigate = useNavigate()
  const { t } = useLanguage()
  const { group_id, group_name, standings = [] } = group
  const [hoveredTeam, setHoveredTeam] = useState(null)

  return (
    <div
      className="rounded-xl p-4 cursor-pointer"
      style={{
        backgroundColor: '#1a1a1a',
        border: '1px solid #2a2a2a',
        transition: 'border-color 0.2s ease, transform 0.15s ease',
      }}
      onClick={() => navigate(`/groups/${group_id}`)}
      onMouseEnter={e => { e.currentTarget.style.borderColor = '#3a3a3a'; e.currentTarget.style.transform = 'scale(1.01)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = '#2a2a2a'; e.currentTarget.style.transform = 'scale(1)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-black text-sm tracking-wide" style={{ color: '#00ff87' }}>
          {group_name}
        </h3>
        <span className="text-xs" style={{ color: '#444' }}>{t.groups.detail} →</span>
      </div>

      {/* Teams */}
      <div className="space-y-1.5">
        {standings.map((entry, i) => {
          const qualifies = i < 2
          const isHovered = hoveredTeam === entry.team
          return (
            <div
              key={entry.team}
              className="flex items-center gap-2 rounded-lg px-2 py-1"
              style={{
                backgroundColor: isHovered
                  ? (qualifies ? '#00ff8710' : '#ff444410')
                  : 'transparent',
                border: `1px solid ${isHovered ? (qualifies ? '#00ff8740' : '#ff444440') : 'transparent'}`,
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => { e.stopPropagation(); setHoveredTeam(entry.team) }}
              onMouseLeave={() => setHoveredTeam(null)}
            >
              <div
                className="w-1 h-4 rounded-full shrink-0"
                style={{ backgroundColor: qualifies ? '#00ff87' : '#ff4444', opacity: 0.7 }}
              />
              <span className="text-xs w-3 shrink-0" style={{ color: '#444' }}>{i + 1}</span>
              <span className="text-base shrink-0">{getFlag(entry.team)}</span>
              <span
                className="text-sm font-medium flex-1 truncate"
                style={{ color: qualifies ? '#00ff87' : '#cc4444' }}
              >
                {entry.team}
              </span>
              <div className="text-right shrink-0">
                <span
                  className="text-sm font-black"
                  style={{ color: qualifies ? '#00ff87' : '#555' }}
                >
                  {entry.pts}
                </span>
                <span className="text-xs ml-0.5" style={{ color: '#444' }}>pts</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 pt-3" style={{ borderTop: '1px solid #2a2a2a' }}>
        <span className="text-xs flex items-center gap-1" style={{ color: '#00ff87' }}>
          <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: '#00ff87' }} />
          {t.groups.qualifies}
        </span>
        <span className="text-xs flex items-center gap-1" style={{ color: '#ff4444' }}>
          <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: '#ff4444' }} />
          {t.groups.eliminated}
        </span>
      </div>
    </div>
  )
}
