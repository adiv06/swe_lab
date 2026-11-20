import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import { useAuth } from '../auth/AuthContext.jsx'
import { api } from '../mockApi.js'

export default function ProjectPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [units, setUnits] = useState([])
  const [error, setError] = useState('')
  const [busyUnitId, setBusyUnitId] = useState(null)
  const [deleting, setDeleting] = useState(false)

  async function refresh() {
    const current = await api.getProject(id)
    const currentUnits = current.isMember ? await api.listUnits() : []
    setProject(current)
    setUnits(currentUnits)
  }

  useEffect(() => {
    setProject(null)
    setError('')
    refresh().catch((err) => setError(err.message))
  }, [id])

  async function changeUnit(unitId, action) {
    setError('')
    setBusyUnitId(unitId)
    try {
      if (action === 'checkout') await api.checkoutUnit(id, unitId)
      else await api.checkinUnit(id, unitId)
      await refresh()
    } catch (err) {
      setError(err.message)
      await refresh().catch(() => {})
    } finally {
      setBusyUnitId(null)
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
      <h1>{project.name}</h1>
      <p>Project ID: <code>{project.id}</code></p>
      <p className="project-description">{project.memberIds.length} member(s)</p>
      {error && <p className="error" role="alert">{error}</p>}

      {project.isMember && <section>
        <h2>Hardware units</h2>
        {units.length === 0 ? <p className="form-note">No hardware units have been added.</p> : (
          <div className="table-scroll">
            <table className="hw-table">
              <thead>
                <tr><th>Unit</th><th>Available</th><th>Assigned to</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {units.map((unit) => (
                  <tr key={unit.id}>
                    <td><strong>{unit.name}</strong><small>{unit.id}</small></td>
                    <td>{unit.status === 'available' ? '1 / 1' : '0 / 1'}</td>
                    <td>{unit.projectId || '—'}</td>
                    <td>
                      <Button onClick={() => changeUnit(unit.id, 'checkout')} disabled={busyUnitId === unit.id}>
                        Check out
                      </Button>
                      {unit.projectId === id && (
                        <Button variant="ghost" onClick={() => changeUnit(unit.id, 'checkin')} disabled={busyUnitId === unit.id}>
                          Check in
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>}

      {project.creatorId === user?.id && (
        <section className="project-delete-section">
          <h2>Delete project</h2>
          <p className="form-note">Check in both hardware units before deleting. The project will disappear from every member's list.</p>
          <Button variant="ghost" className="delete-project-button" onClick={handleDelete} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete project'}
          </Button>
        </section>
      )}
    </div>
  )
}
