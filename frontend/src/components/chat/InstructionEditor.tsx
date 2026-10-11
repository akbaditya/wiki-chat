import { useRef, useState } from 'react'
import { errMsg } from '../../lib/format'
import { useOutsideClose } from '../../lib/usePopover'

interface Props {
  value: string
  max: number
  onSave: (value: string) => Promise<void> | void
}

export default function InstructionEditor({ value, max, onSave }: Props) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useOutsideClose(ref, open, () => setOpen(false))

  const toggle = () => {
    if (!open) {
      setDraft(value)
      setErr(null)
    }
    setOpen((o) => !o)
  }

  const save = async (next: string) => {
    setSaving(true)
    setErr(null)
    try {
      await onSave(next.trim())
      setOpen(false)
    } catch (e) {
      setErr(errMsg(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={toggle}
        className="flex h-9 items-center gap-2 rounded-full bg-cream px-3.5 text-sm font-medium shadow-soft transition hover:bg-white"
      >
        Instruction
        {value && <span className="h-2 w-2 rounded-full bg-blue-600" />}
      </button>
      {open && (
        <div className="absolute right-0 top-full z-40 mt-3 w-[min(21rem,calc(100vw-1.5rem))] rounded-3xl bg-white p-4 shadow-lift">
          <p className="mb-2 text-xs text-gray-500">
            Tell me how to answer, for example "Explain like I'm 12" or "Answer like a pirate". It can't change the
            rules: answers stay grounded in Wikipedia and under 350 words.
          </p>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            maxLength={max}
            rows={4}
            placeholder="Optional instruction…"
            className="w-full resize-none rounded-2xl bg-cream p-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-tan"
          />
          <div className="mt-1 flex items-center justify-between text-xs text-gray-400">
            <span>
              {draft.length}/{max}
            </span>
            {err && <span className="text-red-600">{err}</span>}
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={() => save('')}
              disabled={saving}
              className="rounded-full bg-sand px-4 py-1.5 text-sm shadow-soft transition hover:bg-stone disabled:opacity-50"
            >
              Clear
            </button>
            <button
              onClick={() => save(draft)}
              disabled={saving}
              className="rounded-full bg-blue-600 px-4 py-1.5 text-sm text-white shadow-soft transition hover:bg-blue-700 disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  )
}