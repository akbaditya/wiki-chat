import { useRef, useState } from 'react'
import type { Mode } from '../../types'
import ModeToggle from './ModeToggle'

interface Props {
  busy: boolean
  maxChars: number
  mode: Mode
  locked: boolean
  onModeChange: (m: Mode) => void
  onSend: (text: string) => void
  onStop: () => void
}

export default function Composer({ busy, maxChars, mode, locked, onModeChange, onSend, onStop }: Props) {
  const [text, setText] = useState('')
  const ref = useRef<HTMLTextAreaElement>(null)

  const resize = () => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const submit = () => {
    const t = text.trim()
    if (!t || busy) return
    onSend(t)
    setText('')
    requestAnimationFrame(resize)
  }

  return (
    <div className="rounded-3xl bg-white p-3 shadow-lift transition focus-within:ring-2 focus-within:ring-tan">
      <textarea
        ref={ref}
        value={text}
        rows={1}
        maxLength={maxChars}
        placeholder="Ask anything that's on Wikipedia…"
        onChange={(e) => {
          setText(e.target.value)
          resize()
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            submit()
          }
        }}
        className="max-h-40 w-full resize-none bg-transparent px-2 py-1.5 outline-none placeholder:text-gray-400"
      />
      <div className="mt-1 flex items-center justify-between gap-2">
        <ModeToggle mode={mode} locked={locked} disabled={busy} onChange={onModeChange} />
        <div className="flex items-center gap-2">
          {text.length > maxChars * 0.8 && (
            <span className="text-xs text-gray-400">
              {text.length}/{maxChars}
            </span>
          )}
          {busy ? (
            <button
              onClick={onStop}
              className="rounded-full bg-gray-800 px-4 py-1.5 text-sm font-medium text-white shadow-soft transition hover:bg-gray-900"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={submit}
              disabled={!text.trim()}
              className="rounded-full bg-blue-600 px-5 py-1.5 text-sm font-medium text-white shadow-soft transition hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
            >
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  )
}