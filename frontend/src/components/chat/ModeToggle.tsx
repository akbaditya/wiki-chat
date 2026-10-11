import type { Mode } from '../../types'

interface Props {
  mode: Mode
  locked: boolean
  disabled: boolean
  onChange: (m: Mode) => void
}

const seg = 'flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium transition disabled:opacity-60'

export default function ModeToggle({ mode, locked, disabled, onChange }: Props) {
  return (
    <div role="group" aria-label="Answer mode" className="inline-flex gap-0.5 rounded-full bg-sand p-0.5">
      <button
        disabled={disabled}
        onClick={() => onChange('normal')}
        title="Fast: searches Wikipedia and answers"
        className={`${seg} ${mode === 'normal' ? 'bg-white shadow-soft' : 'text-gray-600 hover:text-ink'}`}
      >
        Normal
      </button>
      <button
        disabled={disabled}
        onClick={() => onChange('accurate')}
        title={
          locked
            ? 'Log in to use Pro mode'
            : 'Analyzes your question, rewrites queries when needed, retries weak searches and shows details'
        }
        className={`${seg} ${mode === 'accurate' ? 'bg-white shadow-soft' : 'text-gray-600 hover:text-ink'}`}
      >
        {locked && (
          <svg viewBox="0 0 24 24" className="h-3 w-3" fill="currentColor" aria-hidden="true">
            <path d="M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5Zm-3 8V7a3 3 0 1 1 6 0v3H9Z" />
          </svg>
        )}
        Pro
      </button>
    </div>
  )
}