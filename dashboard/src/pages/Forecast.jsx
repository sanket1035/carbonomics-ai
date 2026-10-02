import { useState } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { AlertTriangle } from 'lucide-react'
import { COLORS, Callout, Card, MODEL_LABEL, Synthetic, fmt, shortDate, useChartTheme } from '../ui.jsx'

const TARGETS = {
  electricity_kwh: { label: 'Electricity (kWh)', unit: 'kWh', kind: 'activity' },
  diesel_litres: { label: 'Generator diesel (L)', unit: 'L', kind: 'activity' },
  emission: { label: 'Emission, Scope 1 + 2 (kg CO₂e)', unit: 'kg CO₂e', kind: 'emission' },
}
const MODELS = ['naive_last_week', 'train_mean', 'random_forest', 'xgboost']

export default function Forecast({ data }) {
  const t = useChartTheme()
  const [target, setTarget] = useState('electricity_kwh')
  const f = data.forecast
  const cfg = TARGETS[target]

  let rows, metrics
  if (cfg.kind === 'activity') {
    rows = f.activity[target].map((r) => {
      const o = { week_start: r.week_start, actual: r[`actual_${target}`] }
      MODELS.forEach((m) => { o[m] = r[`pred_${m}`] })
      return o
    })
    metrics = f.metrics.filter((m) => m.target === target)
  } else {
    rows = f.emission.map((r) => {
      const o = { week_start: r.week_start, actual: r.actual_total_kg }
      MODELS.forEach((m) => { o[m] = r[`emission_pred_${m}`] })
      return o
    })
    metrics = f.emission_metrics
  }
  const best = Math.min(...metrics.map((m) => m.MAE))
  const beatsNaive = Object.entries(f.beats_naive).map(([tg, ms]) => ({ tg, any: Object.values(ms).some(Boolean) }))
  const electricityBeats = beatsNaive.find((b) => b.tg === 'electricity_kwh')?.any

  return (
    <div className="space-y-6">
      <Callout title="Read this before the numbers">
        <div className="flex gap-2">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>
            The weekly data is synthetic (calibrated to real monthly totals), so these scores show that the pipeline works, not real forecasting accuracy.{' '}
            {electricityBeats ? 'At least one model beats the naive last-week guess for electricity.' : 'No model beats the naive last-week guess for electricity.'} Split is time-based: the last 10 weeks are the test set.
          </span>
        </div>
      </Callout>

      <div className="flex flex-wrap gap-2">
        {Object.entries(TARGETS).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setTarget(k)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${target === k ? 'bg-brand-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-800 dark:hover:bg-slate-800'}`}
          >
            {v.label}
          </button>
        ))}
      </div>

      <Card title={`Actual vs predicted: ${cfg.label}`} subtitle="Test weeks only (chronologically after the training weeks)" badge={<Synthetic />}>
        <div className="h-80">
          <ResponsiveContainer>
            <LineChart data={rows} margin={{ left: -5 }}>
              <CartesianGrid stroke={t.grid} vertical={false} />
              <XAxis dataKey="week_start" tickFormatter={shortDate} stroke={t.axis} tickLine={false} />
              <YAxis stroke={t.axis} tickLine={false} axisLine={false} tickFormatter={(v) => fmt(v)} width={64} domain={['auto', 'auto']} />
              <Tooltip contentStyle={t.tip} labelFormatter={shortDate} formatter={(v, n) => [`${fmt(v, 1)} ${cfg.unit}`, n]} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Line isAnimationActive={false} dataKey="actual" name="Actual (synthetic)" stroke={t.actual} strokeWidth={3} dot={{ r: 3 }} />
              {MODELS.map((m) => (
                <Line isAnimationActive={false} key={m} dataKey={m} name={MODEL_LABEL[m]} stroke={COLORS.models[m]} strokeWidth={1.6} dot={false} strokeDasharray={m === 'train_mean' ? '4 4' : undefined} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Metrics on the test weeks" subtitle="MAE, RMSE, R² next to the baselines. Lower MAE/RMSE is better; best MAE is highlighted.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="muted border-b border-slate-200 text-left text-xs uppercase tracking-wide dark:border-slate-800">
                <th className="py-2 pr-4">Model</th><th className="py-2 pr-4 text-right">MAE</th><th className="py-2 pr-4 text-right">RMSE</th><th className="py-2 text-right">R²</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.model} className="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
                  <td className="py-2.5 pr-4 font-medium">
                    <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLORS.models[m.model] }} />
                    {MODEL_LABEL[m.model]}
                    {m.model.endsWith('naive_last_week') && <span className="muted ml-2 text-xs">baseline</span>}
                  </td>
                  <td className={`py-2.5 pr-4 text-right tabular-nums ${m.MAE === best ? 'font-semibold text-emerald-600 dark:text-emerald-400' : ''}`}>{fmt(m.MAE, 1)}</td>
                  <td className="py-2.5 pr-4 text-right tabular-nums">{fmt(m.RMSE, 1)}</td>
                  <td className="py-2.5 text-right tabular-nums">{fmt(m.R2, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted mt-3 text-xs">Emission forecast = predicted activity x emission factor. 38 training weeks, 10 test weeks.</p>
      </Card>
    </div>
  )
}
