import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'
import ServiceStatus from '../ServiceStatus.jsx'

export default function RegisterPage({ serviceStatus }) {
  const [name, setName] = useState('')
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
      const data = await api.register({ name, username, password })
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
          <h1>Set up your project in under a minute.</h1>
          <p>
            Create an account, start or join a project, and start checking out the hardware
            your team needs.
          </p>

          <ul className="auth-feature-list">
            <li>
              <span className="auth-feature-icon">＋</span>
              Create a project and invite your team
            </li>
            <li>
              <span className="auth-feature-icon">✓</span>
              See available units before you request them
            </li>
            <li>
              <span className="auth-feature-icon">↻</span>
              Check hardware back in when you're done
            </li>
          </ul>
        </div>

        <div className="auth-orbit">
          <div className="orbit-node n1">🧰</div>
          <div className="orbit-node n2">🖥️</div>
          <div className="orbit-node n3">🛰️</div>
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">
          <h1>Create your account</h1>
          <p className="auth-subtitle">Join or start managing a project's hardware.</p>
          <ServiceStatus status={serviceStatus} />

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="name">Name</label>
              <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                minLength={3}
                maxLength={32}
                pattern="[A-Za-z0-9_]+"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>

            {error && <p className="error">{error}</p>}

            <button type="submit" className="btn btn-primary auth-submit" disabled={submitting || serviceStatus !== 'online'}>
              {submitting ? 'Creating account...' : 'Register'}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
