interface Props {
  label: string
  value: string | number
  hint?: string
  tone?: 'warn' | 'bad'
}

export default function Stat({ label, value, hint, tone }: Props) {
  const color = tone === 'bad' ? 'text-red-600' : tone === 'warn' ? 'text-amber-600' : ''
  return (
    <div className="rounded-xl bg-white shadow-soft p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`mt-1 text-xl font-semibold ${color}`}>{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-gray-400">{hint}</div>}
    </div>
  )
}