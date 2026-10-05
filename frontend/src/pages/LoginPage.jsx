import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'
import Button from '../components/Button.jsx'
import FormField from '../components/FormField.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'
import ServiceStatus from '../ServiceStatus.jsx'

const FEATURES = [
  { icon: '✓', text: 'Real-time available units per hardware set' },
  { icon: '↻', text: 'Simple checkout / check-in with per-user caps' },
  { icon: '◎', text: 'A clear record of who holds what' },
]

const ORBIT_ICONS = ['🔧', '📦', '🔌']

export default function LoginPage() {
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
    <AuthLayout
      headline="Share hardware across every project, without the spreadsheet."
      description="Track how many units of each kit are available, who's holding what, and check gear in and out as your team's work changes."
      features={FEATURES}
      orbitIcons={ORBIT_ICONS}
    >
      <h1>Welcome back</h1>
      <p className="auth-subtitle">Log in to see your projects and hardware.</p>

      <form onSubmit={handleSubmit}>
        <FormField
          id="username"
          label="Username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && <p className="error">{error}</p>}

        <Button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? 'Logging in...' : 'Log in'}
        </Button>
      </form>

<<<<<<< HEAD
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
=======
      <p className="auth-switch">
        Need an account? <Link to="/register">Register</Link>
      </p>
    </AuthLayout>
>>>>>>> origin/main
  )
}
