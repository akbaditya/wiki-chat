import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import ChatView from '../components/chat/ChatView'
import InstructionEditor from '../components/chat/InstructionEditor'
import Header from '../components/Header'
import Splash from '../components/Splash'
import type { AppMeta } from '../types'

export default function GuestPage() {
  const navigate = useNavigate()
  const [meta, setMeta] = useState<AppMeta | null>(null)
  const [ready, setReady] = useState(false)
  const [persona, setPersona] = useState('')

  useEffect(() => {
    api
      .meta()
      .then(setMeta)
      .catch(() => undefined)
      .finally(() => setReady(true))
  }, [])

  return (
    <div className="flex h-dvh flex-col bg-cream">
      <Header
        actions={
          <InstructionEditor value={persona} max={meta?.max_persona_chars ?? 500} onSave={setPersona} />
        }
      />
      <div className="bg-stone/40 px-4 py-2 text-center text-xs">
        You're a guest: {meta?.guest_message_limit ?? 10} messages per day, nothing is saved.{' '}
        <Link to="/signup" className="font-semibold text-blue-700 underline">
          Sign up
        </Link>{' '}
        for Pro mode and saved chats.
      </div>
      <main className="min-h-0 flex-1">
        {ready ? (
          <ChatView
            kind="guest"
            mode="normal"
            persona={persona}
            meta={meta}
            initialGuestRemaining={meta?.guest_remaining ?? null}
            onModeChange={() => navigate('/login')}
          />
        ) : (
          <Splash />
        )}
      </main>
    </div>
  )
}