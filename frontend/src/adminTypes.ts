export interface MemoryFact {
  id: string
  fact: string
  created_at: string
}

export interface UsageMe {
  tokens_used_today: number
  daily_budget: number
  tokens_remaining: number
}

export interface AdminOverview {
  users: { count: number; max: number }
  max_convos_per_user: number
  conversations: number
  messages: number
  memory_facts: number
  today: {
    tokens: number
    requests: number
    errors: number
    no_result: number
    guest_messages: number
  }
  budgets: { global_daily: number; global_used_today: number; per_user_daily: number }
  providers: { name: string; circuit_open: boolean }[]
  active_lockouts: number
  page_cache_since_restart: { hits: number; misses: number; hit_rate: number }
}

export interface AdminUser {
  id: string
  email: string
  created_at: string
  last_active_at: string | null
  chats: number
  messages: number
  memories: number
  requests: number
  tokens_total: number
  tokens_today: number
}

export interface AdminConv {
  id: string
  mode: string
  created_at: string
  updated_at: string
  messages: number
}

export interface DayPoint {
  day: string
  requests: number
  ok: number
  errors: number
  no_result: number
  other: number
  tokens_in: number
  tokens_out: number
}

export interface LatencyRow {
  node: string
  count: number
  avg_ms: number
  p50_ms: number | null
  p95_ms: number | null
  max_ms: number
}

export interface Metrics {
  days: number
  totals: {
    requests: number
    ok: number
    errors: number
    no_result: number
    other: number
    error_rate: number
    no_result_rate: number
    tokens_in: number
    tokens_out: number
    active_users: number
  }
  daily: DayPoint[]
  request_statuses: Record<string, number>
  latency: LatencyRow[]
  tokens_by_node: { node: string; calls: number; tokens_in: number; tokens_out: number }[]
  providers: { counts: Record<string, number>; primary: string | null; fallback_rate: number }
  modes: {
    mode: string
    requests: number
    avg_latency_ms: number | null
    avg_tokens_per_request: number | null
  }[]
  audience: { guest: number; user: number }
  rate_limits: Record<string, number>
  cache: { pages_total: number; page_cache_hit_rate: number; index_cache_hit_rate: number }
}