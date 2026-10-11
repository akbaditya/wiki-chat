import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError, api } from '../api/client'
import { formatWait } from '../lib/format'
import { icons } from '../lib/icons'
import { useAuth } from '../store/auth'

const input =
  'mt-1.5 w-full rounded-xl bg-cream px-3.5 py-2.5 outline-none transition focus:bg-white focus-visible:ring-2 focus-visible:ring-tan'

export default function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const user = useAuth((s) => s.user)
  const ready = useAuth((s) => s.ready)
  const login = useAuth((s) => s.login)
  const signup = useAuth((s) => s.signup)
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(true)

  useEffect(() => {
    if (mode === 'signup') {
      api.meta().then((m) => setOpen(m.registrations_open)).catch(() => undefined)
    }
  }, [mode])

  if (ready && user) return <Navigate to="/" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'login') await login(email, password)
      else await signup(email, password)
      navigate('/')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message + (err.retryAfter ? ` Try again in about ${formatWait(err.retryAfter)}.` : ''))
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  const isLogin = mode === 'login'
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 p-4">
      <Link to="/" className="flex items-center gap-3">
        <img src={icons.logo} alt="" className="h-10 w-10" />
        <span className="font-brand text-3xl font-normal tracking-wide">Wiki Chat</span>
      </Link>

      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-3xl bg-white p-7 shadow-lift">
        <h1 className="text-xl font-semibold">{isLogin ? 'Welcome back' : 'Create your account'}</h1>

        {!isLogin && !open && (
          <p className="rounded-2xl bg-amber-50 p-3 text-sm text-amber-800">
            Registrations are full. This demo is invite-only, but you can still chat as a guest.
          </p>
        )}

        <label className="block text-sm font-medium">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={input}
          />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input
            type="password"
            required
            minLength={isLogin ? 1 : 8}
            maxLength={128}
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={input}
          />
          {!isLogin && <span className="text-xs font-normal text-gray-500">At least 8 characters.</span>}
        </label>

        {error && <p className="rounded-2xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        <button
          type="submit"
          disabled={busy || (!isLogin && !open)}
          className="w-full rounded-full bg-blue-600 py-2.5 font-medium text-white shadow-soft transition hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
        >
          {busy ? 'Please wait…' : isLogin ? 'Log in' : 'Sign up'}
        </button>

        <p className="text-center text-sm text-gray-600">
          {isLogin ? (
            <>
              No account?{' '}
              <Link to="/signup" className="text-blue-700 hover:underline">
                Sign up
              </Link>
            </>
          ) : (
            <>
              Already registered?{' '}
              <Link to="/login" className="text-blue-700 hover:underline">
                Log in
              </Link>
            </>
          )}{' '}
          ·{' '}
          <Link to="/" className="text-blue-700 hover:underline">
            Continue as guest
          </Link>
        </p>
      </form>
    </div>
  )
}