import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Droplet, Factory, Leaf, Sun, Zap } from 'lucide-react'
import { COLORS, Callout, Card, Kpi, Real, fmt, monthName, useChartTheme } from '../ui.jsx'

export default function Overview({ data }) {
  const t = useChartTheme()
  const k = data.kpis
  const rest = k.report_footprint_tco2e - k.covered_tco2e
  const donut = [
    { name: 'Electricity + generator diesel', value: k.covered_tco2e, color: COLORS.electricity },
    { name: 'Rest of footprint (no time series)', value: rest, color: '#cbd5e1' },
  ]
  const monthly = data.real_monthly.map((r) => ({
    month: monthName(r.month),
    Electricity: r.electricity_tco2e,
    'Generator diesel': r.diesel_tco2e,
  }))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Covered emissions" value={fmt(k.covered_tco2e, 1)} unit="tCO₂e / yr" sub="Scope 1 + Scope 2 sources with data" icon={Leaf} badge={<Real />} />
        <Kpi label="Electricity (Scope 2)" value={fmt(k.electricity_tco2e, 1)} unit="tCO₂e" sub={`${fmt(k.electricity_kwh)} kWh purchased`} icon={Zap} badge={<Real />} />
        <Kpi label="Generator diesel (Scope 1)" value={fmt(k.diesel_tco2e, 1)} unit="tCO₂e" sub={`${fmt(k.diesel_litres)} litres`} icon={Droplet} badge={<Real />} />
        <Kpi label="Share of campus footprint" value={fmt(k.covered_share_of_footprint * 100, 1)} unit="%" sub={`of ${fmt(k.report_footprint_tco2e, 2)} tCO₂e (full report)`} icon={Factory} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Monthly emissions, 2025" subtitle="Real monthly totals x emission factor" badge={<Real />} className="lg:col-span-2">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={monthly} margin={{ left: -10 }}>
                <CartesianGrid stroke={t.grid} vertical={false} />
                <XAxis dataKey="month" stroke={t.axis} tickLine={false} />
                <YAxis stroke={t.axis} tickLine={false} axisLine={false} unit=" t" />
                <Tooltip contentStyle={t.tip} formatter={(v) => `${fmt(v, 2)} tCO₂e`} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar isAnimationActive={false} dataKey="Electricity" stackId="a" fill={COLORS.electricity} radius={[0, 0, 0, 0]} />
                <Bar isAnimationActive={false} dataKey="Generator diesel" stackId="a" fill={COLORS.diesel} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="What this dashboard covers" subtitle={`Full footprint ${fmt(k.report_footprint_tco2e, 2)} tCO₂e`}>
          <div className="h-52">
            <ResponsiveContainer>
              <PieChart>
                <Pie isAnimationActive={false} data={donut} dataKey="value" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="none">
                  {donut.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Pie>
                <Tooltip contentStyle={t.tip} formatter={(v) => `${fmt(v, 1)} tCO₂e`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-2 space-y-1.5 text-xs">
            {donut.map((d) => (
              <li key={d.name} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: d.color }} />
                <span className="muted flex-1">{d.name}</span>
                <span className="font-medium">{fmt(d.value, 1)} t</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {data.solar && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Kpi label="Rooftop solar generated" value={fmt(data.solar.annual_kwh)} unit="kWh / yr" sub={`${data.solar.period}, self-consumed`} icon={Sun} badge={<Real />} />
          <Kpi label="Solar avoided emissions" value={fmt(data.solar.annual_avoided_tco2e, 2)} unit="tCO₂e / yr" sub="Reported separately, not netted" icon={Sun} badge={<Real />} />
          <Kpi label="Solar vs purchased electricity" value={fmt(data.solar.share_of_purchased_electricity * 100, 1)} unit="%" sub={`of ${fmt(k.electricity_kwh)} kWh from the grid`} icon={Zap} />
        </div>
      )}

      <Callout tone="blue" title="Not covered here (no time series available)">
        <ul className="list-disc space-y-0.5 pl-5">
          {data.not_covered.map((s) => <li key={s}>{s}</li>)}
        </ul>
        <p className="mt-2 text-xs opacity-80">Source of the full footprint: {k.report_source}.</p>
      </Callout>
    </div>
  )
}
