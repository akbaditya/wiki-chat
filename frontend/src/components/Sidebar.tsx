import { Link } from 'react-router-dom'
import type { Conversation } from '../types'

interface Props {
  conversations: Conversation[]
  activeId?: string
  max: number
  creating: boolean
  open: boolean
  onClose: () => void
  onNew: () => void
  onDelete: (id: string) => void
}

export default function Sidebar({
  conversations,
  activeId,
  max,
  creating,
  open,
  onClose,
  onNew,
  onDelete,
}: Props) {
  const full = conversations.length >= max
  return (
    <>
      {open && <div className="fixed inset-0 z-20 bg-ink/30 md:hidden" onClick={onClose} />}
      <aside
        className={`fixed bottom-0 left-0 top-14 z-30 flex w-72 flex-col bg-sand shadow-lift transition-transform md:static md:z-auto md:translate-x-0 md:shadow-bar ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="p-3">
          <button
            onClick={onNew}
            disabled={full || creating}
            title={full ? `You can have up to ${max} chats. Delete one to start a new chat.` : 'Start a new chat'}
            className="w-full rounded-full bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-soft transition hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
          >
            + New chat
          </button>
          <p className="mt-2 text-center text-xs text-gray-500">
            {conversations.length}/{max} chats
          </p>
        </div>
        <nav className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center rounded-2xl transition ${
                c.id === activeId ? 'bg-white shadow-soft' : 'hover:bg-stone/50'
              }`}
            >
              <Link to={`/c/${c.id}`} onClick={onClose} className="min-w-0 flex-1 px-3.5 py-2.5 text-sm">
                <span className="block truncate">{c.title}</span>
                {c.mode === 'accurate' && (
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-blue-600">Pro</span>
                )}
              </Link>
              <button
                onClick={() => onDelete(c.id)}
                aria-label={`Delete ${c.title}`}
                title="Delete chat"
                className="mr-1.5 rounded-full p-1.5 text-gray-400 transition hover:bg-red-50 hover:text-red-600 md:invisible md:group-hover:visible"
              >
                ✕
              </button>
            </div>
          ))}
        </nav>
      </aside>
    </>
  )
}