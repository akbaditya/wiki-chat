import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { MemoryFact, UsageMe } from '../adminTypes'
import { errMsg, fmtDate, fmtNum } from '../lib/format'
import { useAuth } from '../store/auth'
import Modal from './Modal'

const card = 'rounded-2xl bg-white p-4 shadow-soft'

export default function SettingsModal({ onClose }: { onClose: () => void }) {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const navigate = useNavigate()
  const [facts, setFacts] = useState<MemoryFact[] | null>(null)
  const [usage, setUsage] = useState<UsageMe | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [password, setPassword] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [delError, setDelError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([api.memory.list(), api.usage.me()])
      .then(([f, u]) => {
        if (cancelled) return
        setFacts(f)
        setUsage(u)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(errMsg(e))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleLogout = async () => {
    await logout().catch(() => undefined)
    onClose()
    navigate('/')
  }

  const removeFact = async (id: string) => {
    try {
      await api.memory.remove(id)
      setFacts((prev) => prev?.filter((f) => f.id !== id) ?? prev)
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const clearAll = async () => {
    if (!window.confirm('Delete everything I remember about you?')) return
    try {
      await api.memory.clear()
      setFacts([])
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const deleteAccount = async (e: FormEvent) => {
    e.preventDefault()
    if (!window.confirm('Permanently delete your account, all chats and all memories? This cannot be undone.')) return
    setDeleting(true)
    setDelError(null)
    try {
      await api.account.remove(password)
      useAuth.setState({ user: null }) 
      onClose()
      navigate('/', { replace: true })
    } catch (err) {
      setDelError(errMsg(err))
    } finally {
      setDeleting(false)
    }
  }

  const pct = usage ? Math.min(100, (usage.tokens_used_today / usage.daily_budget) * 100) : 0

  return (
    <Modal title="Settings" onClose={onClose}>
      <div className="space-y-4">
        {error && <p className="rounded-2xl bg-red-50 p-3 text-sm text-red-700 shadow-soft">{error}</p>}

        <section className={card}>
          <p className="text-xs text-gray-500">Signed in as</p>
          <div className="mt-1 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium">{user?.email}</p>
              {user?.role === 'admin' && (
                <span className="mt-1 inline-block rounded-full bg-sand px-2 py-0.5 text-[10px] font-semibold uppercase text-gray-600">
                  Admin
                </span>
              )}
            </div>
            <button
              onClick={handleLogout}
              className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:bg-blue-700"
            >
              Log out
            </button>
          </div>
        </section>

        <section className={card}>
          <h3 className="font-medium">Daily usage</h3>
          {usage ? (
            <>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-sand">
                <div className="h-full rounded-full bg-blue-600" style={{ width: `${pct}%` }} />
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {fmtNum(usage.tokens_used_today)} of {fmtNum(usage.daily_budget)} tokens used today ·{' '}
                {fmtNum(usage.tokens_remaining)} left. Resets at midnight UTC.
              </p>
            </>
          ) : (
            <p className="mt-2 text-sm text-gray-500">Loading…</p>
          )}
        </section>

        <section className={card}>
          <div className="flex items-center justify-between">
            <h3 className="font-medium">What I remember about you</h3>
            {facts && facts.length > 0 && (
              <button onClick={clearAll} className="text-sm text-red-600 hover:underline">
                Delete all
              </button>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            When you share things about yourself, I save short notes to personalise answers. Passwords and
            contact details are never saved. You can remove any note.
          </p>
          {facts === null ? (
            <p className="mt-3 text-sm text-gray-500">Loading…</p>
          ) : facts.length === 0 ? (
            <p className="mt-3 text-sm text-gray-500">Nothing saved yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {facts.map((f) => (
                <li key={f.id} className="flex items-center justify-between gap-3 rounded-xl bg-cream p-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm">{f.fact}</p>
                    <p className="text-xs text-gray-400">{fmtDate(f.created_at)}</p>
                  </div>
                  <button
                    onClick={() => removeFact(f.id)}
                    className="shrink-0 rounded-full bg-white px-3 py-1 text-xs text-red-600 shadow-soft transition hover:bg-red-50"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {user?.role === 'user' && (
          <section className={card}>
            <h3 className="font-medium text-red-700">Delete account</h3>
            <p className="mt-1 text-sm text-gray-600">
              Permanently deletes your account, every chat and message, and everything I remember about you.
            </p>
            <form onSubmit={deleteAccount} className="mt-3 flex flex-wrap gap-2">
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Confirm with your password"
                className="min-w-0 flex-1 rounded-xl bg-cream px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-tan"
              />
              <button
                type="submit"
                disabled={deleting || !password}
                className="rounded-full bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-soft transition hover:bg-red-700 disabled:bg-gray-300"
              >
                {deleting ? 'Deleting…' : 'Delete my account'}
              </button>
            </form>
            {delError && <p className="mt-2 text-sm text-red-700">{delError}</p>}
          </section>
        )}
      </div>
    </Modal>
  )
}