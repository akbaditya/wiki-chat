import { create } from 'zustand'
import { api, setUnauthorizedHandler } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  ready: boolean
  init: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const useAuth = create<AuthState>()((set) => ({
  user: null,
  ready: false,
  init: async () => {
    try {
      set({ user: await api.me(), ready: true })
    } catch {
      set({ user: null, ready: true })
    }
  },
  login: async (email, password) => {
    set({ user: await api.login(email, password) })
  },
  signup: async (email, password) => {
    set({ user: await api.signup(email, password) })
  },
  logout: async () => {
    try {
      await api.logout()
    } finally {
      set({ user: null })
    }
  },
}))

setUnauthorizedHandler(() => useAuth.setState({ user: null }))