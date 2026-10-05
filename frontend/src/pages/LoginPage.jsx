import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'
import ServiceStatus from '../ServiceStatus.jsx'

export default function LoginPage({ serviceStatus }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { setSession } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    if (serviceStatus !== 'online') return
    setError('')
    setSubmitting(true)
    try {
      const data = await api.login({ username, password })
      setSession(data.user)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-split">
      <div className="auth-brand-panel">
        <div className="auth-grid-overlay" />

        <div className="auth-brand-top">
          <span className="brand-mark">HA</span> Hardware Allocator
        </div>

        <div className="auth-brand-mid">
          <h1>Share hardware across every project, without the spreadsheet.</h1>
          <p>
            Track how many units of each kit are available, who's holding what, and check
            gear in and out as your team's work changes.
          </p>

          <ul className="auth-feature-list">
            <li>
              <span className="auth-feature-icon">✓</span>
              Real-time available units per hardware set
            </li>
            <li>
              <span className="auth-feature-icon">↻</span>
              Simple checkout / check-in per project
            </li>
            <li>
              <span className="auth-feature-icon">◎</span>
              A clear record of who holds what
            </li>
          </ul>
        </div>

        <div className="auth-orbit">
          <div className="orbit-node n1">🔧</div>
          <div className="orbit-node n2">📦</div>
          <div className="orbit-node n3">🔌</div>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">
          <h1>Welcome back</h1>
          <p className="auth-subtitle">Log in to see your projects and hardware.</p>
          <ServiceStatus status={serviceStatus} />

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && <p className="error">{error}</p>}

            <button type="submit" className="btn btn-primary auth-submit" disabled={submitting || serviceStatus !== 'online'}>
              {submitting ? 'Logging in...' : 'Log in'}
            </button>
          </form>

          <p className="auth-switch">
            Need an account? <Link to="/register">Register</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
