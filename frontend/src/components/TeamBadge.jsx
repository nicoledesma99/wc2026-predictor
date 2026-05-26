import { getFlag } from '../utils/flags'

export default function TeamBadge({ team, ranking, align = 'left', highlight = false, size = 'md' }) {
  const flag = getFlag(team)
  const isRight = align === 'right'
  const nameSize = size === 'sm' ? 'text-xs' : 'text-sm'
  const flagSize = size === 'sm' ? 'text-lg' : 'text-2xl'

  return (
    <div className={`flex items-center gap-2 min-w-0 ${isRight ? 'flex-row-reverse' : ''}`}>
      <span className={`${flagSize} shrink-0`}>{flag}</span>
      <div className={`min-w-0 ${isRight ? 'text-right' : ''}`}>
        <div
          className={`${nameSize} font-semibold leading-tight truncate`}
          style={{ color: highlight ? '#00ff87' : '#ffffff' }}
        >
          {team}
        </div>
        {ranking && (
          <div className="text-xs leading-tight" style={{ color: '#555' }}>
            #{ranking} FIFA
          </div>
        )}
      </div>
    </div>
  )
}
