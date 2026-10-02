import { createContext, useContext } from 'react'

export const COLORS = {
  electricity: '#0f766e',
  diesel: '#d97706',
  actual: '#0f172a',
  models: {
    naive_last_week: '#64748b',
    train_mean: '#a78bfa',
    random_forest: '#0ea5e9',
    xgboost: '#e11d48',
  },
}

export const MODEL_LABEL = {
  naive_last_week: 'Naive (last week)',
  train_mean: 'Training mean',
  random_forest: 'Random Forest',
  xgboost: 'XGBoost',
}

export const ThemeCtx = createContext({ dark: false })
export const useChartTheme = () => {
  const { dark } = useContext(ThemeCtx)
  return {
    grid: dark ? '#1e293b' : '#e2e8f0',
    axis: dark ? '#94a3b8' : '#64748b',
    tip: { backgroundColor: dark ? '#0f172a' : '#fff', border: `1px solid ${dark ? '#334155' : '#e2e8f0'}`, borderRadius: 12, color: dark ? '#e2e8f0' : '#0f172a' },
    actual: dark ? '#f8fafc' : '#0f172a',
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
  }
  return <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

export const Synthetic = () => <Badge tone="amber">SYNTHETIC</Badge>
export const Real = () => <Badge tone="green">REAL DATA</Badge>

export function Card({ title, subtitle, badge, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
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

export function Kpi({ label, value, unit, sub, icon: Icon, badge }) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="muted text-xs font-medium uppercase tracking-wide">{label}</span>
        {Icon && <span className="rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-slate-800 dark:text-brand-500"><Icon size={16} /></span>}
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">{value}</span>
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
