export type Mode = 'normal' | 'accurate'

export interface User {
  id: string
  email: string
  role: 'user' | 'admin'
}

export interface Conversation {
  id: string
  title: string
  system_message: string
  mode: Mode
  created_at: string
  updated_at: string
}

export interface WikiImage {
  url: string
  full_url: string
  caption: string
  artist: string
  license: string
  source_url: string | null
  wiki_page: string
  score: number
}

export interface Source {
  n: number
  page: string
  section: string
  url: string
  score: number
}

export interface AttemptInfo {
  attempt: number
  strategy: string
  queries: string[]
  found: boolean
  top_score: number
  weak: boolean
}

export interface PageInfo {
  title: string
  url: string
  from_cache: boolean
  index_cached: boolean
  num_chunks: number
}

export interface Details {
  mode: string
  failed: boolean
  analysis: {
    strategy?: string
    reason?: string
    attempts?: AttemptInfo[]
    analyzer_error?: boolean
    kept_attempt?: number
  }
  queries: string[]
  retrieval: {
    top_score?: number
    mean_score?: number
    distinct_pages?: number
    num_chunks?: number
    pages?: PageInfo[]
    cache?: { pages_total: number; page_cache_hits: number; index_cache_hits: number }
  }
  chunks: Source[]
  by_node: Record<string, { calls: number; tokens_in: number; tokens_out: number; latency_ms: number }>
  tokens: { input: number; output: number; total: number }
}

export interface ChatError {
  code: string
  message: string
  retryable: boolean
}

export interface UiMessage {
  id: string
  role: 'human' | 'ai'
  text: string
  images: WikiImage[]
  sources: Source[]
  steps: string[]
  streaming: boolean
  stopped?: boolean
  error?: ChatError
  details?: Details
  provider?: string
  mode?: string
  truncated?: boolean
}

export interface HistoryMessage {
  id: string
  role: 'human' | 'ai'
  content: string
  meta: Record<string, unknown> | null
  created_at: string
}

export interface AppMeta {
  max_convos_per_user: number
  guest_message_limit: number
  guest_remaining: number
  registrations_open: boolean
  max_message_chars: number
  max_persona_chars: number
}