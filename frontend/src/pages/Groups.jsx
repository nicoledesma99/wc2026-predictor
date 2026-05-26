import { useState, useEffect } from 'react'
import api from '../api/client'
import GroupCard from '../components/GroupCard'
import { useLanguage } from '../i18n/LanguageContext'

export default function Groups() {
  const { t } = useLanguage()
  const [groups, setGroups]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    api.get('/api/groups')
      .then(r => { setGroups(r.data.groups); setLoading(false) })
      .catch(() => { setError('No se pudo conectar con la API'); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="text-center space-y-2">
        <div className="text-4xl animate-pulse">⚽</div>
        <p style={{ color: '#555' }}>{t.common.loading}</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="text-center py-24" style={{ color: '#ff4444' }}>{error}</div>
  )

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-black" style={{ color: '#00ff87' }}>{t.groups.title}</h1>
        <span
          className="text-xs px-2 py-1 rounded-full font-medium"
          style={{ backgroundColor: '#00ff8715', color: '#00ff87' }}
        >
          {groups.length} {t.groups.groupsCount}
        </span>
      </div>
      <p className="text-sm mb-6" style={{ color: '#555' }}>{t.groups.subtitle}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {groups.map(group => (
          <GroupCard key={group.group_id} group={group} />
        ))}
      </div>
    </div>
  )
}
