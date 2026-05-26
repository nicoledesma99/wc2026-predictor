import { useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext'

export default function ProbabilityBar({
  probHome, probDraw, probAway,
  homeTeam, awayTeam,
  compact = false,
}) {
  const { t } = useLanguage()
  const [hovered, setHovered] = useState(null)

  const h = Math.round(probHome * 100)
  const d = Math.round(probDraw * 100)
  const a = 100 - h - d

  const segments = [
    { key: 'home', pct: h, bg: '#00ff87', label: t.common.homeWin, name: homeTeam || t.common.home },
    { key: 'draw', pct: d, bg: '#ffaa00', label: t.common.draw,    name: t.common.draw             },
    { key: 'away', pct: a, bg: '#ff4444', label: t.common.awayWin, name: awayTeam || t.common.away },
  ]

  const barH = compact ? 'h-2' : 'h-3'

  return (
    <div className="w-full">
      <div className="relative">
        <div className={`flex rounded-full overflow-hidden w-full ${barH}`}>
          {segments.map(seg => (
            <div
              key={seg.key}
              style={{
                width: `${seg.pct}%`,
                backgroundColor: seg.bg,
                minWidth: seg.pct > 0 ? 3 : 0,
                opacity: hovered && hovered !== seg.key ? 0.4 : 1,
                transition: 'opacity 0.15s ease',
              }}
              className="shrink-0 relative cursor-default"
              onMouseEnter={() => setHovered(seg.key)}
              onMouseLeave={() => setHovered(null)}
            >
              {hovered === seg.key && (
                <div
                  className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 z-20 px-2.5 py-1.5 rounded-lg text-xs whitespace-nowrap pointer-events-none"
                  style={{ backgroundColor: '#111', border: '1px solid #333', color: '#fff', boxShadow: '0 4px 12px #0008' }}
                >
                  <span style={{ color: seg.bg }} className="font-bold">{seg.label}</span>
                  <span className="ml-1.5 font-black">{seg.pct}%</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {!compact && (
        <div className="flex justify-between mt-2">
          <span className="text-xs font-semibold truncate max-w-[38%]" style={{ color: '#00ff87' }}>
            {homeTeam ? `${homeTeam} ` : ''}{h}%
          </span>
          <span className="text-xs font-semibold" style={{ color: '#ffaa00' }}>
            {t.common.draw} {d}%
          </span>
          <span className="text-xs font-semibold truncate max-w-[38%] text-right" style={{ color: '#ff4444' }}>
            {awayTeam ? `${awayTeam} ` : ''}{a}%
          </span>
        </div>
      )}
    </div>
  )
}
