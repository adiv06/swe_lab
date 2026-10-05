import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthLayout from '../components/AuthLayout.jsx'
import Button from '../components/Button.jsx'
import FormField from '../components/FormField.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'
import ServiceStatus from '../ServiceStatus.jsx'

const FEATURES = [
  { icon: '＋', text: 'Create a project and invite your team' },
  { icon: '✓', text: 'See available units before you request them' },
  { icon: '↻', text: "Check hardware back in when you're done" },
]

const ORBIT_ICONS = ['🧰', '🖥️', '🛰️']

export default function RegisterPage() {
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
    <AuthLayout
      headline="Set up your project in under a minute."
      description="Create an account, start or join a project, and start checking out the hardware your team needs."
      features={FEATURES}
      orbitIcons={ORBIT_ICONS}
    >
      <h1>Create your account</h1>
      <p className="auth-subtitle">Join or start managing a project's hardware.</p>

      <form onSubmit={handleSubmit}>
        <FormField
          id="name"
          label="Name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <FormField
          id="username"
          label="Username"
          type="text"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          minLength={3}
          maxLength={32}
          pattern="[A-Za-z0-9_]+"
          required
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />

        {error && <p className="error">{error}</p>}

        <Button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? 'Creating account...' : 'Register'}
        </Button>
      </form>

<<<<<<< HEAD
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
=======
      <p className="auth-switch">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </AuthLayout>
>>>>>>> origin/main
  )
}
