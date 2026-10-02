import { CheckCircle2, Download, XCircle } from 'lucide-react'
import { Badge, Card, fmt } from '../ui.jsx'

function downloadCsv(rows) {
  const cols = Object.keys(rows[0])
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => r[c]).join(','))].join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: 'weekly_emissions_synthetic.csv' })
  a.click()
  URL.revokeObjectURL(url)
}

export default function Quality({ data }) {
  const { qa, meta } = data
  const a = meta.weekly_assumptions
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Automated QA" subtitle="Computed from the pipeline outputs, not hard-coded" className="lg:col-span-1">
          <div className="mb-4 flex items-center gap-3">
            {qa.overall === 'PASS' ? <CheckCircle2 className="text-emerald-500" size={32} /> : <XCircle className="text-rose-500" size={32} />}
            <div>
              <div className="text-2xl font-semibold">{qa.overall}</div>
              <div className="muted text-xs">overall status</div>
            </div>
          </div>
          <ul className="space-y-2">
            {qa.sections.map((s) => (
              <li key={s.title} className="flex items-center justify-between text-sm">
                <span>{s.title}</span>
                <Badge tone={s.status === 'PASS' ? 'green' : 'red'}>{s.status || 'n/a'}</Badge>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="How the weekly data was made" subtitle={meta.weekly_label} className="lg:col-span-2">
          <p className="text-sm leading-relaxed">
            The 12 monthly electricity and diesel totals are real (Energy team log). Each month is spread over its days using the assumptions below,
            then summed to 52 full weeks from 1 Jan 2025 ({meta.weekly_left_out}). Random seed: {meta.seed}.
          </p>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
              <dt className="muted text-xs">Electricity weekday weights</dt>
              <dd className="mt-1 font-medium">Mon-Fri {a.electricity_weekday_weight['Mon-Fri']} · Sat {a.electricity_weekday_weight.Sat} · Sun {a.electricity_weekday_weight.Sun}</dd>
            </div>
            <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50">
              <dt className="muted text-xs">Daily noise (lognormal σ)</dt>
              <dd className="mt-1 font-medium">Electricity {a.electricity_noise_lognormal_sigma} · Diesel {a.diesel_noise_lognormal_sigma}</dd>
            </div>
          </dl>
          <button onClick={() => downloadCsv(data.weekly)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700">
            <Download size={16} /> Download weekly data (CSV, synthetic)
          </button>
        </Card>
      </div>

      <Card title="Full QA report" subtitle="outputs/qa_report.md">
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-4 text-xs leading-relaxed dark:bg-slate-950">{qa.markdown}</pre>
      </Card>
    </div>
  )
}
