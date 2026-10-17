import { createContext, useContext, useEffect, useRef, useState } from 'react'

export const COLORS = {
  electricity: '#0f766e',
  diesel: '#d97706',
  solar: '#ca8a04',
  actual: '#0f172a',
  models: {
    naive_last_week: '#64748b',
    train_mean: '#a78bfa',
    random_forest: '#0ea5e9',
    xgboost: '#e11d48',
    ridge: '#16a34a',
  },
}

export const MODEL_LABEL = {
  naive_last_week: 'Naive (last week)',
  train_mean: 'Training mean',
  random_forest: 'Random Forest',
  xgboost: 'XGBoost',
  ridge: 'Ridge regression',
}

export const ThemeCtx = createContext({ dark: false })
export const useChartTheme = () => {
  const { dark } = useContext(ThemeCtx)
  return {
    grid: dark ? '#1f231f' : '#e6dfcb',
    axis: dark ? '#9aa39b' : '#6b665a',
    tip: { backgroundColor: dark ? '#131513' : '#fffdf8', border: `1px solid ${dark ? '#2a2e2a' : '#e6dfcb'}`, borderRadius: 14, color: dark ? '#e6e8e6' : '#14120d' },
    actual: dark ? '#f5f5f0' : '#14120d',
    rest: dark ? '#3a403a' : '#d9d2bd',
  }
}

export const fmt = (n, d = 0) =>
  n == null || Number.isNaN(n) ? '-' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d })

export const shortDate = (s) => new Date(s).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
export const monthName = (s) => new Date(s + '-01').toLocaleDateString('en-GB', { month: 'short' })

export function Badge({ tone = 'slate', children }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    green: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
    red: 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300',
    blue: 'bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300',
  }
  return <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

export const Synthetic = () => <Badge tone="amber">FAKE DATA</Badge>
export const Real = () => <Badge tone="amber">FAKE DATA</Badge>

export function Card({ title, subtitle, badge, children, className = '' }) {
  return (
    <section className={`card rise ${className}`}>
      {(title || badge) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>}
            {subtitle && <p className="muted mt-0.5 text-xs">{subtitle}</p>}
          </div>
          {badge}
        </header>
      )}
      {children}
    </section>
  )
}

// Counts a number up from 0 once, so a result "lands". Anything that is not a plain number is shown as it is.
function CountUp({ text }) {
  const m = /^(-?)([\d,]*\.?\d+)$/.exec(String(text))
  const target = m ? Number(m[2].replaceAll(',', '')) : null
  const decimals = m && m[2].includes('.') ? m[2].split('.')[1].length : 0
  const [now, setNow] = useState(target == null ? null : 0)
  const raf = useRef(0)
  useEffect(() => {
    if (target == null) return undefined
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setNow(target); return undefined }
    const start = performance.now()
    const tick = (t) => {
      const k = Math.min(1, (t - start) / 900)
      setNow(target * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [target])
  if (target == null) return text
  return `${m[1]}${fmt(now, decimals)}`
}

export function Kpi({ label, value, unit, sub, icon: Icon, badge }) {
  return (
    <div className="card rise transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center justify-between">
        <span className="muted font-mono text-[10.5px] font-medium uppercase tracking-[.08em]">{label}</span>
        {Icon && <span className="rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-slate-800 dark:text-brand-500"><Icon size={16} /></span>}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white tabular-nums"><CountUp text={value} /></span>
        {unit && <span className="muted text-sm">{unit}</span>}
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="muted text-xs">{sub}</span>
        {badge}
      </div>
    </div>
  )
}

export function Callout({ tone = 'amber', title, children }) {
  const tones = {
    amber: 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200',
    blue: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200',
  }
  return (
    <div className={`rounded-xl border p-4 text-sm ${tones[tone]}`}>
      {title && <div className="mb-1 font-semibold">{title}</div>}
      <div className="leading-relaxed">{children}</div>
    </div>
  )
}
