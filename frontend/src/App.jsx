import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import AppHeader from './components/AppHeader.jsx'
import PrivateRoute from './components/PrivateRoute.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProjectPage from './pages/ProjectPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'

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
      {user && <AppHeader serviceStatus={serviceStatus} userName={user.name} onLogout={logout} />}
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
