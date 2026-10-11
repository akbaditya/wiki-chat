import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Splash from './components/Splash'
import AdminPage from './pages/AdminPage'
import AppPage from './pages/AppPage'
import AuthPage from './pages/AuthPage'
import GuestPage from './pages/GuestPage'
import { useAuth } from './store/auth'

function Home() {
  const { user, ready } = useAuth()
  if (!ready) return <Splash />
  return user ? <AppPage /> : <GuestPage />
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  if (!ready) return <Splash />
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth()
  if (!ready) return <Splash />
  if (!user) return <Navigate to="/login" replace />
  return user.role === 'admin' ? <>{children}</> : <Navigate to="/" replace />
}

export default function App() {
  const init = useAuth((s) => s.init)
  useEffect(() => {
    void init()
  }, [init])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="/c/:id"
          element={
            <RequireAuth>
              <AppPage />
            </RequireAuth>
          }
        />
        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <AdminPage />
            </RequireAdmin>
          }
        />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/signup" element={<AuthPage mode="signup" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}