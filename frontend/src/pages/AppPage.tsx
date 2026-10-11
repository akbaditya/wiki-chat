import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import ChatView from '../components/chat/ChatView'
import InstructionEditor from '../components/chat/InstructionEditor'
import Header from '../components/Header'
import Sidebar from '../components/Sidebar'
import Splash from '../components/Splash'
import { errMsg } from '../lib/format'
import type { AppMeta, Conversation, Mode } from '../types'

export default function AppPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [convs, setConvs] = useState<Conversation[] | null>(null)
  const [meta, setMeta] = useState<AppMeta | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [creating, setCreating] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setConvs(await api.conversations.list())
    } catch (e) {
      setNotice(errMsg(e))
    }
  }, [])

  useEffect(() => {
    void refresh()
    api.meta().then(setMeta).catch(() => undefined)
  }, [refresh])

  // "/" opens the most recent chat
  useEffect(() => {
    if (convs && !id && convs.length > 0) navigate(`/c/${convs[0].id}`, { replace: true })
  }, [convs, id, navigate])

  const patchLocal = (cid: string, patch: Partial<Conversation>) =>
    setConvs((prev) => prev?.map((c) => (c.id === cid ? { ...c, ...patch } : c)) ?? prev)

  const maxChats = meta?.max_convos_per_user ?? 10
  const active = convs?.find((c) => c.id === id)

  const newChat = async () => {
    setCreating(true)
    try {
      const c = await api.conversations.create({})
      setConvs((prev) => [c, ...(prev ?? [])])
      setSidebarOpen(false)
      navigate(`/c/${c.id}`)
    } catch (e) {
      setNotice(errMsg(e))
    } finally {
      setCreating(false)
    }
  }

  const deleteChat = async (cid: string) => {
    if (!window.confirm('Delete this chat? This cannot be undone.')) return
    try {
      await api.conversations.remove(cid)
      const rest = (convs ?? []).filter((c) => c.id !== cid)
      setConvs(rest)
      if (cid === id) navigate(rest.length > 0 ? `/c/${rest[0].id}` : '/', { replace: true })
    } catch (e) {
      setNotice(errMsg(e))
    }
  }

  const changeMode = async (m: Mode) => {
    if (!active || active.mode === m) return
    const prev = active.mode
    patchLocal(active.id, { mode: m }) 
    try {
      patchLocal(active.id, await api.conversations.update(active.id, { mode: m }))
    } catch (e) {
      patchLocal(active.id, { mode: prev })
      setNotice(errMsg(e))
    }
  }

  const saveInstruction = async (p: string) => {
    if (!active) return
    patchLocal(active.id, await api.conversations.update(active.id, { system_message: p }))
  }

  let content
  if (convs === null) {
    content = <Splash />
  } else if (!id) {
    content =
      convs.length === 0 ? (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
          <h2 className="text-xl font-semibold">No chats yet</h2>
          <p className="text-sm text-gray-500">Start a chat to ask questions about anything on Wikipedia.</p>
          <button
            onClick={newChat}
            disabled={creating}
            className="rounded-full bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-soft transition hover:bg-blue-700 disabled:bg-gray-300"
          >
            + New chat
          </button>
        </div>
      ) : (
        <Splash />
      )
  } else if (!active) {
    content = (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <h2 className="text-xl font-semibold">Chat not found</h2>
        <p className="text-sm text-gray-500">It may have been deleted, or it isn't yours.</p>
        <Link to="/" className="text-blue-700 hover:underline">
          Back to your chats
        </Link>
      </div>
    )
  } else {
    content = (
      <ChatView
        key={active.id}
        kind="user"
        conversationId={active.id}
        mode={active.mode}
        persona={active.system_message}
        meta={meta}
        onModeChange={changeMode}
        onTurnFinished={refresh}
      />
    )
  }

  return (
    <div className="flex h-dvh flex-col bg-cream">
      <Header
        onMenu={() => setSidebarOpen(true)}
        actions={
          active && (
            <InstructionEditor
              key={active.id}
              value={active.system_message}
              max={meta?.max_persona_chars ?? 500}
              onSave={saveInstruction}
            />
          )
        }
      />
      {notice && (
        <div className="flex items-center justify-between bg-red-50 px-4 py-2 text-sm text-red-800">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} aria-label="Dismiss">
            ✕
          </button>
        </div>
      )}
      <div className="relative flex min-h-0 flex-1">
        <Sidebar
          conversations={convs ?? []}
          activeId={id}
          max={maxChats}
          creating={creating}
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNew={newChat}
          onDelete={deleteChat}
        />
        <main className="min-w-0 flex-1">{content}</main>
      </div>
    </div>
  )
}