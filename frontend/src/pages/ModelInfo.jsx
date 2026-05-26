import { useState, useEffect, useRef } from 'react'
import api from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

function useVisible(threshold = 0.15) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true) },
      { threshold }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [threshold])
  return [ref, visible]
}

function TimelineStep({ step, index, color = '#00ff87' }) {
  const [ref, visible] = useVisible()
  return (
    <div
      ref={ref}
      className="flex gap-4"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(20px)',
        transition: `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`,
      }}
    >
      {/* Left: line + circle */}
      <div className="flex flex-col items-center" style={{ minWidth: 32 }}>
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-black shrink-0"
          style={{ backgroundColor: '#0f0f0f', border: `2px solid ${color}`, color }}
        >
          {step.num}
        </div>
        {index < 4 && (
          <div className="w-px flex-1 mt-1" style={{ backgroundColor: '#2a2a2a', minHeight: 24 }} />
        )}
      </div>

      {/* Right: card */}
      <div
        className="rounded-xl p-4 mb-4 flex-1"
        style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-black text-sm text-white">{step.title}</h3>
          <span
            className="text-xs px-2 py-0.5 rounded-full shrink-0 font-mono"
            style={{ backgroundColor: '#0f0f0f', color, border: `1px solid ${color}40` }}
          >
            {step.tag}
          </span>
        </div>
        <p className="text-xs leading-relaxed" style={{ color: '#888' }}>{step.body}</p>
      </div>
    </div>
  )
}

function MetricBar({ label, value, color, note }) {
  const [ref, visible] = useVisible()
  const pct = Math.round(value * 100)
  return (
    <div ref={ref}>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-medium" style={{ color: '#aaa' }}>{label}</span>
        <span className="text-sm font-black" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-2 rounded-full mb-1" style={{ backgroundColor: '#2a2a2a' }}>
        <div
          className="h-2 rounded-full"
          style={{
            width: visible ? `${pct}%` : '0%',
            backgroundColor: color,
            transition: 'width 0.8s ease',
          }}
        />
      </div>
      {note && <p className="text-xs" style={{ color: '#555' }}>{note}</p>}
    </div>
  )
}

function TechCard({ item }) {
  const [ref, visible] = useVisible()
  return (
    <div
      ref={ref}
      className="rounded-xl p-4 text-center"
      style={{
        backgroundColor: '#1a1a1a',
        border: '1px solid #2a2a2a',
        opacity: visible ? 1 : 0,
        transform: visible ? 'scale(1)' : 'scale(0.95)',
        transition: 'opacity 0.4s ease, transform 0.4s ease',
      }}
    >
      <div className="text-2xl mb-2">{item.icon}</div>
      <div className="text-xs font-bold text-white mb-1">{item.name}</div>
      <div className="text-xs" style={{ color: '#555' }}>{item.desc}</div>
    </div>
  )
}

export default function ModelInfo() {
  const { t } = useLanguage()
  const [info, setInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/model-info')
      .then(r => { setInfo(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center py-24">
      <div className="text-4xl animate-pulse">⚽</div>
    </div>
  )

  const perClass = info?.per_class_metrics
    ? Object.entries(info.per_class_metrics).map(([, m], i) => ({
        label: t.model.classLabels[i],
        color: t.model.classColors[i],
        precision: m.precision ?? 0,
        recall: m.recall ?? 0,
        f1: m.f1 ?? 0,
      }))
    : []

  return (
    <div className="space-y-10">

      {/* Section 1: Header */}
      <div className="pt-6">
        <div
          className="inline-block text-xs font-mono px-2 py-1 rounded mb-3"
          style={{ backgroundColor: '#00ff8715', color: '#00ff87', border: '1px solid #00ff8730' }}
        >
          {info?.model_name ?? 'Logistic Regression'} · {info ? `CV ${(info.cv_mean * 100).toFixed(1)}%` : '…'}
        </div>
        <h1 className="text-3xl font-black tracking-tight mb-2" style={{ color: '#00ff87' }}>
          {t.model.pageTitle}
        </h1>
        <p className="text-base font-medium text-white max-w-lg">{t.model.pageSubtitle}</p>
      </div>

      {/* Section 2: Timeline */}
      <div>
        <div className="space-y-0">
          {t.model.steps.map((step, i) => (
            <TimelineStep key={step.num} step={step} index={i} />
          ))}
        </div>
      </div>

      {/* Section 3: Metrics */}
      {perClass.length > 0 && (
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#555' }}>
            {t.model.metricsTitle}
          </h2>
          <div className="rounded-xl p-4" style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}>
            {/* Top-level stats */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              {[
                { label: 'Accuracy', value: info?.accuracy, color: '#00ff87' },
                { label: 'CV Score', value: info?.cv_mean, color: '#ffaa00' },
                { label: 'F1 Macro', value: info?.f1_macro, color: '#888' },
              ].map(m => (
                <div key={m.label} className="text-center">
                  <div className="text-xl font-black" style={{ color: m.color }}>
                    {m.value != null ? `${(m.value * 100).toFixed(1)}%` : '–'}
                  </div>
                  <div className="text-xs" style={{ color: '#555' }}>{m.label}</div>
                </div>
              ))}
            </div>

            {/* Per-class bars */}
            <div className="space-y-5">
              {perClass.map(cls => (
                <div key={cls.label}>
                  <div className="text-xs font-bold mb-2" style={{ color: cls.color }}>{cls.label}</div>
                  <div className="space-y-2">
                    <MetricBar label="Precision" value={cls.precision} color={cls.color} />
                    <MetricBar label="Recall" value={cls.recall} color={cls.color} />
                    <MetricBar label="F1" value={cls.f1} color={cls.color} />
                  </div>
                </div>
              ))}
            </div>

            <p className="text-xs mt-4 pt-3" style={{ color: '#555', borderTop: '1px solid #2a2a2a' }}>
              ⚠️ {t.model.metricsNote}
            </p>
          </div>
        </div>
      )}

      {/* Section 4: Tech stack */}
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#555' }}>
          {t.model.techTitle}
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {t.model.techStack.map(item => (
            <TechCard key={item.name} item={item} />
          ))}
        </div>
      </div>

      {/* Section 5: Author */}
      <div
        className="rounded-xl p-5"
        style={{ backgroundColor: '#1a1a1a', border: '1px solid #2a2a2a' }}
      >
        <h2 className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#555' }}>
          {t.model.authorTitle}
        </h2>
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-xl font-black shrink-0"
            style={{ backgroundColor: '#00ff8715', color: '#00ff87', border: '1px solid #00ff8730' }}
          >
            NL
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-black text-white text-sm">{t.model.author}</div>
            <div className="text-xs mt-0.5" style={{ color: '#666' }}>{t.model.authorRole}</div>
            <div className="flex gap-3 mt-2">
              <a
                href={t.model.githubLink}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-medium flex items-center gap-1"
                style={{ color: '#00ff87' }}
              >
                <span>↗</span> {t.model.githubLabel}
              </a>
              <a
                href={t.model.linkedinLink}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-medium flex items-center gap-1"
                style={{ color: '#00aaff' }}
              >
                <span>↗</span> {t.model.linkedinLabel}
              </a>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}
