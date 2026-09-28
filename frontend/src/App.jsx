import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import ProjectPage from './pages/ProjectPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="loading-text">Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const { user, logout } = useAuth()
  const isAuthPage = !user

  return (
    <div className={isAuthPage ? 'app app-auth' : 'app'}>
      {user && (
        <header className="topbar">
          <Link to="/" className="brand">
            <span className="brand-mark">HA</span> Hardware Allocator
          </Link>
          <div className="topbar-actions">
            <span className="user-chip">{user.name}</span>
            <button className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
      )}
      <main className={isAuthPage ? 'content content-auth' : 'content'}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <DashboardPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/projects/:id"
            element={
              <PrivateRoute>
                <ProjectPage />
              </PrivateRoute>
            }
          />
        </Routes>
      </main>
    </div>
  )
}
