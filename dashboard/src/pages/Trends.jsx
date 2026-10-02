import { Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { COLORS, Callout, Card, Real, Synthetic, fmt, monthName, shortDate, useChartTheme } from '../ui.jsx'

const compact = (v) => (Math.abs(v) >= 1000 ? `${fmt(v / 1000, v % 1000 ? 1 : 0)}k` : fmt(v))

const Chart = ({ children, data, xKey = 'week_start', xFmt = shortDate, unit }) => {
  const t = useChartTheme()
  return (
    <div className="h-64">
      <ResponsiveContainer>
        {children({ t, xAxis: <XAxis dataKey={xKey} tickFormatter={xFmt} stroke={t.axis} tickLine={false} minTickGap={28} />, yAxis: <YAxis stroke={t.axis} tickLine={false} axisLine={false} tickFormatter={compact} unit={unit} width={52} />, data })}
      </ResponsiveContainer>
    </div>
  )
}

export default function Trends({ data }) {
  const monthly = data.real_monthly.map((r) => ({ ...r, label: monthName(r.month) }))
  const weekly = data.weekly.map((w) => ({ ...w, scope1_t: w.scope1_kg / 1000, scope2_t: w.scope2_kg / 1000 }))
  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Electricity purchased, monthly" subtitle="kWh, Energy team log" badge={<Real />}>
          <Chart data={monthly} xKey="label" xFmt={(v) => v}>
            {({ t, xAxis, yAxis, data: d }) => (
              <BarChart data={d} margin={{ left: -10 }}>
                <CartesianGrid stroke={t.grid} vertical={false} />{xAxis}{yAxis}
                <Tooltip contentStyle={t.tip} formatter={(v) => `${fmt(v)} kWh`} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
                <Bar isAnimationActive={false} dataKey="electricity_kwh" name="Electricity" fill={COLORS.electricity} radius={[6, 6, 0, 0]} />
              </BarChart>
            )}
          </Chart>
        </Card>
        <Card title="Generator diesel, monthly" subtitle="Litres, Energy team log" badge={<Real />}>
          <Chart data={monthly} xKey="label" xFmt={(v) => v}>
            {({ t, xAxis, yAxis, data: d }) => (
              <BarChart data={d} margin={{ left: -10 }}>
                <CartesianGrid stroke={t.grid} vertical={false} />{xAxis}{yAxis}
                <Tooltip contentStyle={t.tip} formatter={(v) => `${fmt(v)} L`} cursor={{ fill: 'rgba(148,163,184,0.12)' }} />
                <Bar isAnimationActive={false} dataKey="dg_diesel_litres" name="Diesel" fill={COLORS.diesel} radius={[6, 6, 0, 0]} />
              </BarChart>
            )}
          </Chart>
        </Card>
      </div>

      <Callout title="Weekly charts below are SYNTHETIC">
        Only the monthly totals are real. The weekly values spread each month over its days using assumed weekday and noise patterns, then sum to 52 full weeks from 1 Jan 2025 (31 Dec is left out).
      </Callout>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Weekly electricity" subtitle="kWh per week" badge={<Synthetic />}>
          <Chart data={weekly}>
            {({ t, xAxis, yAxis, data: d }) => (
              <AreaChart data={d} margin={{ left: -10 }}>
                <defs><linearGradient id="ge" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={COLORS.electricity} stopOpacity={0.35} /><stop offset="100%" stopColor={COLORS.electricity} stopOpacity={0} /></linearGradient></defs>
                <CartesianGrid stroke={t.grid} vertical={false} />{xAxis}{yAxis}
                <Tooltip contentStyle={t.tip} labelFormatter={shortDate} formatter={(v) => `${fmt(v)} kWh`} />
                <Area isAnimationActive={false} type="monotone" dataKey="electricity_kwh" name="Electricity" stroke={COLORS.electricity} strokeWidth={2} fill="url(#ge)" />
              </AreaChart>
            )}
          </Chart>
        </Card>
        <Card title="Weekly generator diesel" subtitle="Litres per week" badge={<Synthetic />}>
          <Chart data={weekly}>
            {({ t, xAxis, yAxis, data: d }) => (
              <LineChart data={d} margin={{ left: -10 }}>
                <CartesianGrid stroke={t.grid} vertical={false} />{xAxis}{yAxis}
                <Tooltip contentStyle={t.tip} labelFormatter={shortDate} formatter={(v) => `${fmt(v, 1)} L`} />
                <Line isAnimationActive={false} type="monotone" dataKey="diesel_litres" name="Diesel" stroke={COLORS.diesel} strokeWidth={2} dot={false} />
              </LineChart>
            )}
          </Chart>
        </Card>
      </div>

      <Card title="Weekly emissions by scope" subtitle="tCO₂e per week (activity x factor)" badge={<Synthetic />}>
        <Chart data={weekly}>
          {({ t, xAxis, yAxis, data: d }) => (
            <AreaChart data={d} margin={{ left: -10 }}>
              <CartesianGrid stroke={t.grid} vertical={false} />{xAxis}{yAxis}
              <Tooltip contentStyle={t.tip} labelFormatter={shortDate} formatter={(v) => `${fmt(v, 2)} tCO₂e`} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Area isAnimationActive={false} type="monotone" stackId="1" dataKey="scope2_t" name="Scope 2 electricity" stroke={COLORS.electricity} fill={COLORS.electricity} fillOpacity={0.35} />
              <Area isAnimationActive={false} type="monotone" stackId="1" dataKey="scope1_t" name="Scope 1 generator diesel" stroke={COLORS.diesel} fill={COLORS.diesel} fillOpacity={0.5} />
            </AreaChart>
          )}
        </Chart>
      </Card>
    </div>
  )
}
