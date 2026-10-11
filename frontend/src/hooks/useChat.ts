import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { streamChat } from '../api/stream'
import { errMsg, uid } from '../lib/format'
import type { Details, HistoryMessage, Mode, Source, UiMessage, WikiImage } from '../types'

interface Options {
  kind: 'user' | 'guest'
  mode: Mode
  conversationId?: string
  persona: string
  initialGuestRemaining?: number | null
  onFinished?: () => void
}

function blank(role: UiMessage['role'], text = '', streaming = false): UiMessage {
  return { id: uid(), role, text, images: [], sources: [], steps: [], streaming }
}

function fromHistory(m: HistoryMessage): UiMessage {
  const meta = (m.meta ?? {}) as {
    images?: WikiImage[]
    sources?: Source[]
    details?: Details | null
    provider?: string
    mode?: string
    failed?: string
  }
  return {
    id: m.id,
    role: m.role,
    text: meta.failed ? '' : m.content,
    images: meta.images ?? [],
    sources: meta.sources ?? [],
    steps: [],
    streaming: false,
    details: meta.details ?? undefined,
    provider: meta.provider,
    mode: meta.mode,
    error: meta.failed
      ? { code: meta.failed, message: m.content, retryable: false }
      : undefined,
  }
}

export function useChat({
  kind,
  conversationId,
  persona,
  mode,
  initialGuestRemaining = null,
  onFinished,
}: Options) {
  const [messages, setMessages] = useState<UiMessage[]>([])
  const [loading, setLoading] = useState(kind === 'user')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [guestRemaining, setGuestRemaining] = useState<number | null>(initialGuestRemaining)

  const abortRef = useRef<AbortController | null>(null)
  const busyRef = useRef(false)
  const messagesRef = useRef<UiMessage[]>([])
  const onFinishedRef = useRef(onFinished)

  useEffect(() => {
    messagesRef.current = messages
    onFinishedRef.current = onFinished
  })

  useEffect(() => {
    let cancelled = false
    if (kind === 'user' && conversationId) {
      api.conversations
        .messages(conversationId)
        .then((rows) => {
          if (!cancelled) setMessages(rows.map(fromHistory))
        })
        .catch((e: unknown) => {
          if (!cancelled) setLoadError(errMsg(e))
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }
    return () => {
      cancelled = true
      abortRef.current?.abort()
    }
  }, [kind, conversationId])

  const send = useCallback(
    async (text: string) => {
      const message = text.trim()
      if (!message || busyRef.current) return
      if (kind === 'user' && !conversationId) return

      busyRef.current = true
      setBusy(true)

      const ai: UiMessage = { ...blank('ai', '', true), mode }
      setMessages((prev) => [...prev, blank('human', message), ai])
      const patch = (fn: (m: UiMessage) => UiMessage) =>
        setMessages((prev) => prev.map((m) => (m.id === ai.id ? fn(m) : m)))

      const ac = new AbortController()
      abortRef.current = ac

      const url =
        kind === 'user' ? `/conversations/${conversationId}/stream` : '/chat/guest/stream'
      const body =
        kind === 'user'
          ? { message }
          : { message, system_message: persona || undefined }

      await streamChat(
        url,
        body,
        {
          onStatus: (s) => patch((m) => ({ ...m, steps: [...m.steps, s] })),
          onImages: (images) => patch((m) => ({ ...m, images })),
          onToken: (t) => patch((m) => ({ ...m, text: m.text + t })),
          onMetadata: (d) =>
            patch((m) => ({
              ...m,
              text: d.answer, 
              sources: d.sources ?? [],
              provider: d.provider ?? undefined,
              mode: d.mode ?? m.mode,
              truncated: d.truncated,
            })),
          onDetails: (details) => patch((m) => ({ ...m, details })),
          onError: (error) => {
            patch((m) => ({ ...m, error }))
            if (kind === 'guest' && /guest limit/i.test(error.message)) setGuestRemaining(0)
          },
          onDone: (d) => {
            if (typeof d.guest_remaining === 'number') setGuestRemaining(d.guest_remaining)
          },
        },
        ac.signal,
      )

      const stopped = ac.signal.aborted
      patch((m) => ({ ...m, streaming: false, stopped: stopped || undefined }))
      busyRef.current = false
      setBusy(false)
      if (!stopped) onFinishedRef.current?.()
    },
    [kind, conversationId, persona, mode],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  const retry = useCallback(() => {
    const lastHuman = [...messagesRef.current].reverse().find((m) => m.role === 'human')
    if (lastHuman) void send(lastHuman.text)
  }, [send])

  return { messages, loading, loadError, busy, guestRemaining, send, stop, retry }
}