import { Fragment, useState } from 'react'
import { api } from '../../api/client'
import type { AdminConv, AdminUser } from '../../adminTypes'
import { errMsg, fmtDate, fmtNum } from '../../lib/format'

interface Props {
  users: AdminUser[]
  onDeleteUser: (u: AdminUser) => Promise<void>
  onChanged: () => void
}

export default function UsersTable({ users, onDeleteUser, onChanged }: Props) {
  const [open, setOpen] = useState<string | null>(null)
  const [convs, setConvs] = useState<Record<string, AdminConv[]>>({})
  const [error, setError] = useState<string | null>(null)

  const toggle = async (id: string) => {
    if (open === id) {
      setOpen(null)
      return
    }
    setOpen(id)
    setError(null)
    try {
      const rows = await api.admin.userConversations(id)
      setConvs((prev) => ({ ...prev, [id]: rows }))
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const deleteChat = async (userId: string, convId: string) => {
    if (!window.confirm('Delete this chat permanently?')) return
    try {
      await api.admin.deleteConversation(convId)
      setConvs((prev) => ({ ...prev, [userId]: (prev[userId] ?? []).filter((c) => c.id !== convId) }))
      onChanged()
    } catch (e) {
      setError(errMsg(e))
    }
  }

  const th = 'px-3 py-2 text-left font-medium'
  return (
    <div className="overflow-x-auto rounded-xl bg-white shadow-soft">
      {error && <p className="bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      <table className="w-full min-w-[820px] text-sm">
        <thead className="bg-gray-50 text-xs text-gray-500">
          <tr>
            <th className={th}>Email</th>
            <th className={th}>Chats</th>
            <th className={th}>Messages</th>
            <th className={th}>Memories</th>
            <th className={th}>Requests</th>
            <th className={th}>Tokens today</th>
            <th className={th}>Tokens total</th>
            <th className={th}>Last active</th>
            <th className={th}>Joined</th>
            <th className={th} />
          </tr>
        </thead>
        <tbody>
          {users.length === 0 && (
            <tr>
              <td colSpan={10} className="p-4 text-center text-gray-500">
                No users yet.
              </td>
            </tr>
          )}
          {users.map((u) => (
            <Fragment key={u.id}>
              <tr className="border-t">
                <td className="px-3 py-2 font-medium">{u.email}</td>
                <td className="px-3 py-2">{u.chats}</td>
                <td className="px-3 py-2">{u.messages}</td>
                <td className="px-3 py-2">{u.memories}</td>
                <td className="px-3 py-2">{u.requests}</td>
                <td className="px-3 py-2">{fmtNum(u.tokens_today)}</td>
                <td className="px-3 py-2">{fmtNum(u.tokens_total)}</td>
                <td className="px-3 py-2">{fmtDate(u.last_active_at)}</td>
                <td className="px-3 py-2">{fmtDate(u.created_at)}</td>
                <td className="whitespace-nowrap px-3 py-2 text-right">
                  <button onClick={() => toggle(u.id)} className="mr-2 text-blue-600 hover:underline">
                    {open === u.id ? 'Hide chats' : 'Chats'}
                  </button>
                  <button
                    onClick={() => void onDeleteUser(u)}
                    className="rounded border px-2 py-1 text-xs text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </td>
              </tr>
              {open === u.id && (
                <tr className="bg-gray-50">
                  <td colSpan={10} className="px-4 py-3">
                    {!convs[u.id] ? (
                      <span className="text-gray-500">Loading…</span>
                    ) : convs[u.id].length === 0 ? (
                      <span className="text-gray-500">No chats.</span>
                    ) : (
                      <table className="w-full text-xs">
                        <thead className="text-gray-500">
                          <tr>
                            <th className="py-1 text-left font-medium">Mode</th>
                            <th className="text-left font-medium">Messages</th>
                            <th className="text-left font-medium">Created</th>
                            <th className="text-left font-medium">Updated</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {convs[u.id].map((c) => (
                            <tr key={c.id} className="border-t">
                              <td className="py-1 capitalize">{c.mode}</td>
                              <td>{c.messages}</td>
                              <td>{fmtDate(c.created_at)}</td>
                              <td>{fmtDate(c.updated_at)}</td>
                              <td className="text-right">
                                <button
                                  onClick={() => deleteChat(u.id, c.id)}
                                  className="text-red-600 hover:underline"
                                >
                                  Delete chat
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                    <p className="mt-2 text-[11px] text-gray-400">
                      Chat content and titles are not shown, by design.
                    </p>
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}