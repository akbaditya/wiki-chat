import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useChat } from '../../hooks/useChat'
import { icons } from '../../lib/icons'
import type { AppMeta, Details, Mode, Source } from '../../types'
import Composer from './Composer'
import DetailsDrawer from './DetailsDrawer'
import MessageBubble from './MessageBubble'
import SourcesModal from './SourcesModal'

const EXAMPLES = [
  'Who invented the telephone?',
  'What causes the northern lights?',
  'Compare the Roman Empire and the Han dynasty',
]

interface Props {
  kind: 'user' | 'guest'
  conversationId?: string
  mode: Mode
  persona: string
  meta: AppMeta | null
  initialGuestRemaining?: number | null
  onModeChange: (m: Mode) => void
  onTurnFinished?: () => void
}

export default function ChatView({
  kind,
  conversationId,
  mode,
  persona,
  meta,
  initialGuestRemaining = null,
  onModeChange,
  onTurnFinished,
}: Props) {
  const { messages, loading, loadError, busy, guestRemaining, send, stop, retry } = useChat({
    kind,
    conversationId,
    persona,
    mode,
    initialGuestRemaining,
    onFinished: onTurnFinished,
  })
  const [details, setDetails] = useState<Details | null>(null)
  const [sources, setSources] = useState<Source[] | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const stick = useRef(true) 

  useEffect(() => {
    const el = scrollRef.current
    if (el && stick.current) el.scrollTop = el.scrollHeight
  }, [messages])

  const onScroll = () => {
    const el = scrollRef.current
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }

  const handleSend = (text: string) => {
    stick.current = true
    void send(text)
  }

  const guestOut = kind === 'guest' && guestRemaining === 0
  const lastId = messages.at(-1)?.id

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} onScroll={onScroll} className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
          {loading && <p className="text-center text-sm text-gray-500">Loading messages…</p>}
          {loadError && <p className="text-center text-sm text-red-600">{loadError}</p>}

          {!loading && !loadError && messages.length === 0 && (
            <div className="py-12 text-center">
              <img src={icons.logo} alt="" className="mx-auto mb-4 h-14 w-14" />
              <h2 className="text-xl font-semibold">Ask me anything from Wikipedia</h2>
              <p className="mt-1 text-sm text-gray-500">
                I search Wikipedia, show relevant images, then answer with sources.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2.5">
                {EXAMPLES.map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="rounded-full bg-white px-4 py-2 text-sm shadow-soft transition hover:shadow-lift"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              msg={m}
              isLast={m.id === lastId}
              busy={busy}
              isGuest={kind === 'guest'}
              onRetry={retry}
              onDetails={setDetails}
              onSources={setSources}
            />
          ))}
        </div>
      </div>

      <div className="px-3 pb-3 pt-1 sm:px-4">
        <div className="mx-auto max-w-3xl">
          {guestOut ? (
            <p className="rounded-2xl bg-sand p-4 text-center text-sm shadow-soft">
              You've used all your free guest messages for today.{' '}
              <Link to="/signup" className="font-medium text-blue-700 underline">
                Sign up
              </Link>{' '}
              or{' '}
              <Link to="/login" className="font-medium text-blue-700 underline">
                log in
              </Link>{' '}
              to keep chatting.
            </p>
          ) : (
            <Composer
              busy={busy}
              maxChars={meta?.max_message_chars ?? 1000}
              mode={mode}
              locked={kind === 'guest'}
              onModeChange={onModeChange}
              onSend={handleSend}
              onStop={stop}
            />
          )}
          <p className="mt-2 text-center text-[11px] text-gray-400">
            {kind === 'guest' && guestRemaining !== null
              ? `${guestRemaining} guest message${guestRemaining === 1 ? '' : 's'} left today · `
              : ''}
            Answers come from Wikipedia and can still be wrong. Check the sources.
          </p>
        </div>
      </div>

      {details && <DetailsDrawer details={details} onClose={() => setDetails(null)} />}
      {sources && <SourcesModal sources={sources} onClose={() => setSources(null)} />}
    </div>
  )
}