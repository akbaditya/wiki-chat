import { useRef, useState } from 'react'
import { useOutsideClose } from '../../lib/usePopover'

function Spinner() {
  return (
    <svg className="h-3.5 w-3.5 animate-spin text-blue-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function LiveSteps({ steps }: { steps: string[] }) {
  if (steps.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Spinner /> Starting…
      </div>
    )
  }
  return (
    <ul className="space-y-1.5 text-sm text-gray-500">
      {steps.map((s, i) => {
        const current = i === steps.length - 1
        return (
          <li key={i} className="flex items-center gap-2">
            {current ? <Spinner /> : <span className="w-3.5 text-center text-green-600">✓</span>}
            <span className={current ? 'text-gray-800' : ''}>{s}</span>
          </li>
        )
      })}
    </ul>
  )
}

export function StepsPopover({ steps }: { steps: string[] }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useOutsideClose(ref, open, () => setOpen(false))

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-full bg-sand px-3 py-1 text-xs font-medium text-gray-700 shadow-soft transition hover:bg-stone"
      >
        {open ? 'Hide steps' : 'Show steps'}
      </button>
      {open && (
        <div className="absolute bottom-full left-0 z-20 mb-2 max-h-64 w-72 overflow-y-auto rounded-2xl bg-white p-3 text-sm shadow-lift">
          <ul className="space-y-1.5">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-2 text-gray-700">
                <span className="text-green-600">✓</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}