import { useState, useEffect } from 'react'
import api from '../api/client'
import { getFlag } from '../utils/flags'
import { useLanguage } from '../i18n/LanguageContext'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'

const GREEN = '#00ff87'
const YELLOW = '#ffaa00'

function rankColor(i) {
  if (i === 0) return GREEN
  if (i <= 2) return YELLOW
  return '#888'
}

function CustomTooltip({ active, payload, t }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const win  = Math.round(d.avg_win_prob * 100)
  const draw = Math.round(Math.min(0.22, 1 - d.avg_win_prob - 0.08) * 100)
  const loss = 100 - win - draw
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs space-y-1"
      style={{ backgroundColor: '#111', border: '1px solid #333', boxShadow: '0 4px 12px #0008' }}
    >
      <div className="font-bold text-white mb-1.5">{getFlag(d.team)} {d.team}</div>
      <div className="flex justify-between gap-3">
        <span style={{ color: GREEN }}>{t.favorites.win}</span>
        <span className="font-black text-white">{win}%</span>
      </div>
      <div className="flex justify-between gap-3">
        <span style={{ color: YELLOW }}>{t.favorites.draw}</span>
        <span className="font-black text-white">{draw}%</span>
      </div>
      <div className="flex justify-between gap-3">
        <span style={{ color: '#ff4444' }}>{t.favorites.loss}</span>
        <span className="font-black text-white">{loss}%</span>
      </div>
      {d.ranking && (
        <div className="pt-1 mt-1" style={{ borderTop: '1px solid #2a2a2a', color: '#555' }}>
          {t.favorites.ranking} #{d.ranking}
        </div>
      )}
    </div>
  )
}

export default function Favorites() {
  const { t } = useLanguage()
  const [favorites, setFavorites] = useState([])
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    api.get('/api/favorites')
      .then(r => { setFavorites(r.data.favorites); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="text-4xl animate-pulse">⚽</div>
    </div>
  )

  const chartData = favorites.slice(0, 10).map(f => ({
    ...f,
    name: f.team.length > 13 ? f.team.slice(0, 12) + '…' : f.team,
    pct: Math.round(f.avg_win_prob * 100),
  }))

  const minPct = Math.max(0,   Math.min(...chartData.map(d => d.pct)) - 5)
  const maxPct = Math.min(100, Math.max(...chartData.map(d => d.pct)) + 8)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-black" style={{ color: '#00ff87' }}>{t.favorites.title}</h1>
        <p className="text-xs mt-1" style={{ color: '#555' }}>
          Top {favorites.length} {t.favorites.subtitle.toLowerCase()}
        </p>
      </div>

      {/* Chart */}
      <div className="rounded-xl p-4 mb-6" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
        <h2 className="text-xs font-bold mb-4 uppercase tracking-wide" style={{ color: '#555' }}>
          {t.favorites.chartTitle}
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 48, top: 0, bottom: 0 }}>
            <XAxis
              type="number"
              domain={[minPct, maxPct]}
              tickFormatter={v => `${v}%`}
              tick={{ fontSize: 10, fill: '#555' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={95}
              tick={{ fontSize: 11, fill: '#aaa' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip t={t} />} cursor={{ fill: '#ffffff06' }} />
            <Bar dataKey="pct" radius={[0, 4, 4, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={GREEN} fillOpacity={i === 0 ? 1 : Math.max(0.4, 1 - i * 0.06)} />
              ))}
              <LabelList
                dataKey="pct"
                position="right"
                formatter={v => `${v}%`}
                style={{ fill: '#aaa', fontSize: 11, fontWeight: 700 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Ranking list */}
      <div className="space-y-2">
        {favorites.map((fav, i) => (
          <div
            key={fav.team}
            className="rounded-xl px-4 py-3 flex items-center gap-3"
            style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a', transition: 'border-color 0.2s ease' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#3a3a3a'}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#2a2a2a'}
          >
            <span className="text-lg font-black w-7 text-center shrink-0" style={{ color: rankColor(i) }}>
              {i + 1}
            </span>
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className="text-xl shrink-0">{getFlag(fav.team)}</span>
              <div className="min-w-0">
                <div className="font-semibold text-sm text-white truncate">{fav.team}</div>
                {fav.ranking && (
                  <div className="text-xs" style={{ color: '#555' }}>{t.favorites.ranking} #{fav.ranking}</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4 shrink-0">
              <div className="text-right hidden sm:block">
                <div className="text-xs" style={{ color: '#555' }}>{t.favorites.group}</div>
                <div className="text-sm font-bold text-white">{fav.group || '–'}</div>
              </div>
              <div className="text-right">
                <div className="text-xs" style={{ color: '#555' }}>{t.favorites.avgWin}</div>
                <div className="text-lg font-black" style={{ color: rankColor(i) }}>
                  {Math.round(fav.avg_win_prob * 100)}%
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-center mt-6" style={{ color: '#333' }}>{t.favorites.note}</p>
    </div>
  )
}
