import { fetchEventSource } from '@microsoft/fetch-event-source'
import { ApiError, toApiError } from './client'
import type { ChatError, Details, Source, WikiImage } from '../types'

export interface MetadataEvent {
  answer: string
  sources: Source[]
  provider: string | null
  mode?: string
  truncated?: boolean
  interrupted?: boolean
}

export interface DoneEvent {
  request_id: string
  guest_remaining?: number
}

export interface StreamHandlers {
  onStatus: (message: string) => void
  onImages: (images: WikiImage[]) => void
  onToken: (text: string) => void
  onMetadata: (data: MetadataEvent) => void
  onDetails: (data: Details) => void
  onError: (error: ChatError) => void
  onDone: (data: DoneEvent) => void
}

class StreamClosed extends Error {}

export async function streamChat(
  url: string,
  body: object,
  h: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  let finished = false
  try {
    await fetchEventSource('/api' + url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
      openWhenHidden: true, 
      async onopen(res) {
        if (res.ok && res.headers.get('content-type')?.includes('text/event-stream')) return
        throw await toApiError(res)
      },
      onmessage(ev) {
        if (!ev.data) return
        const data: unknown = JSON.parse(ev.data)
        switch (ev.event) {
          case 'status':
            h.onStatus((data as { message: string }).message)
            break
          case 'images':
            h.onImages((data as { images: WikiImage[] }).images)
            break
          case 'token':
            h.onToken((data as { text: string }).text)
            break
          case 'metadata':
            h.onMetadata(data as MetadataEvent)
            break
          case 'details':
            h.onDetails(data as Details)
            break
          case 'error':
            h.onError(data as ChatError)
            break
          case 'done':
            finished = true
            h.onDone(data as DoneEvent)
            break
        }
      },
      onclose() {
        throw new StreamClosed() 
      },
      onerror(err) {
        throw err 
      },
    })
  } catch (err) {
    if (signal.aborted) return
    if (err instanceof StreamClosed) {
      if (!finished) {
        h.onError({
          code: 'connection_lost',
          message: 'The connection was interrupted. Please try again.',
          retryable: true,
        })
      }
      return
    }
    if (err instanceof ApiError) {
      h.onError({
        code: `http_${err.status}`,
        message: err.message,
        retryable: err.status >= 500 || (err.status === 429 && (err.retryAfter ?? 999) <= 60),
      })
      return
    }
    h.onError({
      code: 'network',
      message: 'Could not reach the server. Check your connection and try again.',
      retryable: true,
    })
  }
}