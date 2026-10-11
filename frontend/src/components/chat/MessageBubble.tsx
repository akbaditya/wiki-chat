import { memo } from 'react'
import { icons } from '../../lib/icons'
import type { Details, Source, UiMessage } from '../../types'
import ImageStrip from './ImageStrip'
import Markdown from './Markdown'
import { LiveSteps, StepsPopover } from './Steps'

interface Props {
  msg: UiMessage
  isLast: boolean
  busy: boolean
  isGuest: boolean
  onRetry: () => void
  onDetails: (d: Details) => void
  onSources: (s: Source[]) => void
}

const chip =
  'rounded-full bg-sand px-3 py-1 text-xs font-medium text-gray-700 shadow-soft transition hover:bg-stone'
const avatar = 'h-9 w-9 shrink-0 rounded-full bg-white object-cover shadow-soft'

function MessageBubble({ msg, isLast, busy, isGuest, onRetry, onDetails, onSources }: Props) {
  if (msg.role === 'human') {
    return (
      <div className="flex items-end justify-end gap-2.5">
        <div className="max-w-[80%] whitespace-pre-wrap break-words rounded-3xl rounded-br-md bg-tan px-5 py-3 font-chat text-[15px] leading-relaxed text-ink shadow-soft">
          {msg.text}
        </div>
        <img src={isGuest ? icons.guest : icons.user} alt={isGuest ? 'Guest' : 'You'} className={avatar} />
      </div>
    )
  }

  const pro = msg.mode === 'accurate'
  const hasText = msg.text.length > 0
  const liveSteps = msg.streaming && !hasText && !msg.error
  const showFooter = !msg.streaming && (hasText || msg.steps.length > 0 || msg.details)

  return (
    <div className="flex gap-2.5">
      <img src={icons.bot} alt="Assistant" className={`mt-1 ${avatar}`} />
      <div className="min-w-0 flex-1 space-y-3">
        {msg.images.length > 0 && <ImageStrip images={msg.images} />}

        {liveSteps && <LiveSteps steps={msg.steps} />}

        {hasText && (
          <div
            className={`break-words rounded-3xl rounded-tl-md px-5 py-4 font-chat text-[15px] leading-relaxed shadow-soft ${
              pro ? 'bg-pro' : 'bg-sand'
            }`}
          >
            <Markdown>{msg.text}</Markdown>
            {msg.streaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-gray-400 align-middle" />
            )}
          </div>
        )}

        {msg.error && (
          <div className="rounded-2xl bg-red-50 p-3.5 text-sm text-red-800 shadow-soft">
            <p>{msg.error.message}</p>
            {isLast && !busy && msg.error.retryable && (
              <button
                onClick={onRetry}
                className="mt-2 rounded-full bg-red-600 px-4 py-1 text-white shadow-soft transition hover:bg-red-700"
              >
                Try again
              </button>
            )}
          </div>
        )}

        {showFooter && (
          <div className="flex flex-wrap items-center gap-2">
            {msg.sources.length > 0 && (
              <button onClick={() => onSources(msg.sources)} className={chip}>
                Sources
              </button>
            )}
            {msg.steps.length > 0 && <StepsPopover steps={msg.steps} />}
            {msg.details && (
              <button onClick={() => onDetails(msg.details!)} className={chip}>
                Details
              </button>
            )}
            {pro && (
              <span className="rounded-full bg-pro px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-700 shadow-soft">
                Pro
              </span>
            )}
            {msg.provider && <span className="text-[11px] text-gray-400">{msg.provider}</span>}
            {msg.truncated && <span className="text-[11px] text-gray-400">Shortened to fit the word limit</span>}
            {msg.stopped && <span className="text-[11px] text-gray-400">Stopped</span>}
          </div>
        )}
      </div>
    </div>
  )
}

export default memo(MessageBubble)