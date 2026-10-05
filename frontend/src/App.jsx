import { useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import ServiceStatus from './ServiceStatus.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProjectPage from './pages/ProjectPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'

function PrivateRoute({ children, serviceStatus }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="loading-text">Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  if (serviceStatus !== 'online') {
    return <div className="service-gate"><ServiceStatus status={serviceStatus} /></div>
  }
  return children
}

export default function App() {
  const { user, logout } = useAuth()
  const [serviceStatus, setServiceStatus] = useState('checking')
  const isAuthPage = !user

  useEffect(() => {
    let active = true
    async function checkStatus() {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' })
        if (active) setServiceStatus(response.ok ? 'online' : 'offline')
      } catch {
        if (active) setServiceStatus('offline')
      }
    }
    checkStatus()
    const interval = setInterval(checkStatus, 5000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  return (
    <div className={isAuthPage ? 'app app-auth' : 'app'}>
      {user && (
        <header className="topbar">
          <Link to="/" className="brand">
            <span className="brand-mark">HA</span> Hardware Allocator
          </Link>
          <div className="topbar-actions">
            <ServiceStatus status={serviceStatus} />
            <span className="user-chip">{user.name}</span>
            <button className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
      )}
      <main className={isAuthPage ? 'content content-auth' : 'content'}>
        <Routes>
          <Route path="/login" element={<LoginPage serviceStatus={serviceStatus} />} />
          <Route path="/register" element={<RegisterPage serviceStatus={serviceStatus} />} />
          <Route
            path="/"
            element={
              <PrivateRoute serviceStatus={serviceStatus}>
                <DashboardPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/projects/:id"
            element={
              <PrivateRoute serviceStatus={serviceStatus}>
                <ProjectPage />
              </PrivateRoute>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
