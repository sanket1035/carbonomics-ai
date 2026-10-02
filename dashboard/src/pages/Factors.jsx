import { useState } from 'react'
import { CheckCircle2, Search, XCircle } from 'lucide-react'
import { Badge, Callout, Card, fmt } from '../ui.jsx'

export default function Factors({ data }) {
  const [q, setQ] = useState('')
  const rows = data.factors.filter((r) => `${r.name} ${r.source} ${r.scope}`.toLowerCase().includes(q.toLowerCase()))
  const unverified = data.factors.filter((r) => !r.verified)
  return (
    <div className="space-y-6">
      {unverified.length > 0 && (
        <Callout title={`${unverified.length} factors are not verified yet`}>
          {unverified.map((u) => u.name).join(', ')}: kept from the earlier code base and not found in the KKWIEER Master Data. Confirm the source before quoting them in a report. They are not used for the electricity and diesel numbers on this dashboard.
        </Callout>
      )}
      <Card title="Emission factors" subtitle="Every factor has a value, unit, source and version">
        <div className="relative mb-4 max-w-sm">
          <Search size={16} className="muted absolute left-3 top-2.5" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search factor, source or scope"
            className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-950" />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px] text-sm">
            <thead>
              <tr className="muted border-b border-slate-200 text-left text-xs uppercase tracking-wide dark:border-slate-800">
                <th className="py-2 pr-3">Activity</th><th className="py-2 pr-3">Scope</th><th className="py-2 pr-3 text-right">Factor</th><th className="py-2 pr-3">Unit</th><th className="py-2 pr-3">Source</th><th className="py-2 pr-3">Version</th><th className="py-2">Verified</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-b border-slate-100 align-top last:border-0 dark:border-slate-800/60">
                  <td className="py-2.5 pr-3 font-medium">{r.name.replace(/_/g, ' ')}</td>
                  <td className="py-2.5 pr-3"><Badge>{r.scope}</Badge></td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{fmt(r.factor, 3)}</td>
                  <td className="muted py-2.5 pr-3">{r.output}</td>
                  <td className="py-2.5 pr-3 text-xs leading-relaxed">{r.source}</td>
                  <td className="muted py-2.5 pr-3 text-xs">{r.version}</td>
                  <td className="py-2.5">
                    {r.verified ? <CheckCircle2 size={18} className="text-emerald-500" aria-label="verified" /> : <XCircle size={18} className="text-amber-500" aria-label="not verified" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
