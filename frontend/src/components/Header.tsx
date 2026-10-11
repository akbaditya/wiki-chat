import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { icons } from '../lib/icons'
import { useAuth } from '../store/auth'
import SettingsModal from './SettingsModal'

interface Props {
  onMenu?: () => void
  actions?: ReactNode 
}

const pill =
  'flex h-9 items-center gap-2 rounded-full bg-cream px-3.5 text-sm font-medium shadow-soft transition hover:bg-white'

export default function Header({ onMenu, actions }: Props) {
  const user = useAuth((s) => s.user)
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <header className="relative z-30 flex h-14 shrink-0 items-center justify-between bg-sand px-3 shadow-bar sm:px-5">
        <div className="flex items-center gap-2">
          {onMenu && (
            <button
              onClick={onMenu}
              aria-label="Open chats"
              className="grid h-9 w-9 place-items-center rounded-full bg-cream text-lg shadow-soft md:hidden"
            >
              ☰
            </button>
          )}
          <Link to="/" className="flex items-center gap-2.5">
            <img src={icons.logo} alt="" className="h-8 w-8" />
            <span className="font-brand text-2xl font-normal leading-none tracking-wide">Wiki Chat</span>
          </Link>
        </div>

        <div className="flex items-center gap-2">
          {actions}
          {user?.role === 'admin' && (
            <Link to="/admin" className={pill}>
              <img src={icons.analytics} alt="" className="h-4 w-4" />
              <span className="hidden sm:inline">Admin</span>
            </Link>
          )}
          {user ? (
            <button
              onClick={() => setSettingsOpen(true)}
              aria-label="Settings"
              title="Settings"
              className="grid h-9 w-9 place-items-center rounded-full bg-cream shadow-soft transition hover:bg-white"
            >
              <img src={icons.settings} alt="" className="h-5 w-5" />
            </button>
          ) : (
            <>
              <Link to="/login" className={pill}>
                Log in
              </Link>
              <Link
                to="/signup"
                className="flex h-9 items-center rounded-full bg-blue-600 px-4 text-sm font-medium text-white shadow-soft transition hover:bg-blue-700"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </header>
      {settingsOpen && <SettingsModal onClose={() => setSettingsOpen(false)} />}
    </>
  )
}