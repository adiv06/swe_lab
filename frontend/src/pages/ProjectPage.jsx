import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../api.js'

export default function ProjectPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [sets, setSets] = useState([])
  const [quantities, setQuantities] = useState({})
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busySetId, setBusySetId] = useState(null)
  const [joining, setJoining] = useState(false)
  const [deleting, setDeleting] = useState(false)

  async function refresh() {
    const [current, hardware] = await Promise.all([api.getProject(id), api.listHardware()])
    setProject(current)
    setSets(hardware)
  }

  useEffect(() => {
    setProject(null)
    setError('')
    setMessage('')
    refresh().catch((err) => setError(err.message))
  }, [id])

  async function changeHardware(set, action) {
    setError('')
    setMessage('')
    const raw = quantities[set.id] ?? ''
    const quantity = Number(raw)
    if (!Number.isInteger(quantity) || quantity < 1) {
      setError('Enter a whole number of units (1 or more)')
      return
    }
    setBusySetId(set.id)
    try {
      if (action === 'checkout') await api.checkoutHardware(id, set.id, quantity)
      else await api.checkinHardware(id, set.id, quantity)
      setMessage(`${action === 'checkout' ? 'Checked out' : 'Checked in'} ${quantity} unit(s) of ${set.name}.`)
      setQuantities((q) => ({ ...q, [set.id]: '' }))
    } catch (err) {
      setError(err.message)
    } finally {
      await refresh().catch(() => {})
      setBusySetId(null)
    }
  }

  async function handleJoin() {
    setError('')
    setJoining(true)
    try {
      await api.joinProject(id)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setJoining(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete project ${project.name}? It will disappear for every member.`)) return
    setError('')
    setDeleting(true)
    try {
      await api.deleteProject(id)
      navigate('/')
    } catch (err) {
      setError(err.message)
      setDeleting(false)
    }
  }

  if (!project) return error
    ? <p className="error" role="alert">{error} <Link to="/">Back to projects</Link></p>
    : <p className="loading-text">Loading...</p>

  return (
    <div>
      <p><Link to="/">← All projects</Link></p>
      <h1>{project.name}</h1>
      <p>Project ID: <code>{project.id}</code></p>
      {project.description && <p className="project-description">{project.description}</p>}
      <p className="project-description">Members: {project.memberIds.join(', ')}</p>
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="success" role="status">{message}</p>}

      {!project.isMember ? (
        <section>
          <h2>Hardware</h2>
          <p className="form-note">You are not a member of this project. Join it to check hardware in or out.</p>
          <Button onClick={handleJoin} disabled={joining}>{joining ? 'Joining...' : 'Join project'}</Button>
        </section>
      ) : (
        <section>
          <h2>Hardware sets</h2>
          <div className="table-scroll">
            <table className="hw-table">
              <thead>
                <tr>
                  <th>Hardware set</th>
                  <th>Capacity</th>
                  <th>Available</th>
                  <th>Checked out by this project</th>
                  <th>Quantity</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sets.map((set) => (
                  <tr key={set.id}>
                    <td><strong>{set.name}</strong><small>{set.id}</small></td>
                    <td>{set.capacity}</td>
                    <td data-testid={`available-${set.id}`}><strong>{set.available}</strong> / {set.capacity}</td>
                    <td>{project.hardware[set.id] || 0}</td>
                    <td>
                      <input
                        type="number"
                        min="1"
                        step="1"
                        aria-label={`Quantity for ${set.name}`}
                        value={quantities[set.id] ?? ''}
                        onChange={(e) => setQuantities((q) => ({ ...q, [set.id]: e.target.value }))}
                      />
                    </td>
                    <td>
                      <Button onClick={() => changeHardware(set, 'checkout')} disabled={busySetId === set.id}>
                        Check out
                      </Button>
                      <Button variant="ghost" onClick={() => changeHardware(set, 'checkin')} disabled={busySetId === set.id}>
                        Check in
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {project.creatorId === user?.id && (
        <section className="project-delete-section">
          <h2>Delete project</h2>
          <p className="form-note">Check in all hardware before deleting. The project will disappear from every member's list.</p>
          <Button variant="ghost" className="delete-project-button" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete project'}
          </Button>
        </section>
      )}
    </div>
  )
}
