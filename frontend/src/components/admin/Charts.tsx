import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DayPoint } from '../../adminTypes'

function Frame({ title, children }: { title: string; children: React.ReactElement }) {
  return (
    <div className="rounded-xl bg-white shadow-soft p-3">
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      <ResponsiveContainer width="100%" height={240}>
        {children}
      </ResponsiveContainer>
    </div>
  )
}

const label = (d: DayPoint) => ({ ...d, label: d.day.slice(5) }) 

export function RequestsChart({ data }: { data: DayPoint[] }) {
  return (
    <Frame title="Requests per day">
      <BarChart data={data.map(label)}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" fontSize={12} />
        <YAxis allowDecimals={false} fontSize={12} width={32} />
        <Tooltip />
        <Legend />
        <Bar dataKey="ok" name="Answered" stackId="r" fill="#16a34a" />
        <Bar dataKey="no_result" name="Nothing found" stackId="r" fill="#f59e0b" />
        <Bar dataKey="other" name="Other" stackId="r" fill="#9ca3af" />
        <Bar dataKey="errors" name="Errors" stackId="r" fill="#dc2626" />
      </BarChart>
    </Frame>
  )
}

export function TokensChart({ data }: { data: DayPoint[] }) {
  return (
    <Frame title="Tokens per day">
      <BarChart data={data.map(label)}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" fontSize={12} />
        <YAxis fontSize={12} width={44} />
        <Tooltip />
        <Legend />
        <Bar dataKey="tokens_in" name="Input" stackId="t" fill="#2563eb" />
        <Bar dataKey="tokens_out" name="Output" stackId="t" fill="#7c3aed" />
      </BarChart>
    </Frame>
  )
}