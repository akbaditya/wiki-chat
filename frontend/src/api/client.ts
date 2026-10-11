import type { AppMeta, Conversation, HistoryMessage, Mode, User } from '../types'
import type {
  AdminConv,
  AdminOverview,
  AdminUser,
  MemoryFact,
  Metrics,
  UsageMe,
} from '../adminTypes'

const BASE = '/api'

export class ApiError extends Error {
  status: number
  retryAfter?: number

  constructor(status: number, message: string, retryAfter?: number) {
    super(message)
    this.status = status
    this.retryAfter = retryAfter
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') message = data.detail
    else if (Array.isArray(data?.detail)) message = 'Please check your input and try again.'
  } catch {
  }
  const ra = Number(res.headers.get('retry-after'))
  return new ApiError(res.status, message, Number.isFinite(ra) && ra > 0 ? ra : undefined)
}

let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Check your connection.')
  }
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) onUnauthorized?.()
    throw await toApiError(res)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  meta: () => request<AppMeta>('GET', '/meta'),
  me: () => request<User>('GET', '/auth/me'),
  login: (email: string, password: string) =>
    request<User>('POST', '/auth/login', { email, password }),
  signup: (email: string, password: string) =>
    request<User>('POST', '/auth/signup', { email, password }),
  logout: () => request<void>('POST', '/auth/logout'),
  conversations: {
    list: () => request<Conversation[]>('GET', '/conversations'),
    create: (body: { title?: string; system_message?: string; mode?: Mode } = {}) =>
      request<Conversation>('POST', '/conversations', body),
    update: (
      id: string,
      body: Partial<Pick<Conversation, 'title' | 'system_message' | 'mode'>>,
    ) => request<Conversation>('PATCH', `/conversations/${id}`, body),
    remove: (id: string) => request<void>('DELETE', `/conversations/${id}`),
    messages: (id: string) =>
      request<HistoryMessage[]>('GET', `/conversations/${id}/messages`),
  },
  memory: {
    list: () => request<MemoryFact[]>('GET', '/memory'),
    remove: (id: string) => request<void>('DELETE', `/memory/${id}`),
    clear: () => request<void>('DELETE', '/memory'),
  },
  usage: { me: () => request<UsageMe>('GET', '/usage/me') },
  account: {
    remove: (password: string) => request<void>('POST', '/account/delete', { password }),
  },
  admin: {
    overview: () => request<AdminOverview>('GET', '/admin/overview'),
    users: () => request<AdminUser[]>('GET', '/admin/users'),
    userConversations: (id: string) =>
      request<AdminConv[]>('GET', `/admin/users/${id}/conversations`),
    deleteUser: (id: string) => request<void>('DELETE', `/admin/users/${id}`),
    deleteConversation: (id: string) => request<void>('DELETE', `/admin/conversations/${id}`),
    metrics: (days: number) => request<Metrics>('GET', `/admin/metrics?days=${days}`),
    clearLockouts: () =>
      request<{ cleared: number }>('POST', '/admin/security/clear-lockouts'),
  },
}