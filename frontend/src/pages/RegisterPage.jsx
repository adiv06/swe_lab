import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'

export default function RegisterPage() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { setSession } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const data = await api.register({ name, email, password })
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

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="name">Name</label>
              <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
                required
              />
            </div>

            {error && <p className="error">{error}</p>}

            <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
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
