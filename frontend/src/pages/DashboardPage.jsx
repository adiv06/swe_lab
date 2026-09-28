import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../mockApi.js'

export default function DashboardPage() {
  const [myProjects, setMyProjects] = useState([])
  const [otherProjects, setOtherProjects] = useState([])
  const [newProjectName, setNewProjectName] = useState('')
  const [error, setError] = useState('')

  async function refresh() {
    const [mine, all] = await Promise.all([api.myProjects(), api.listProjects()])
    setMyProjects(mine)
    setOtherProjects(all.filter((p) => !p.isMember))
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    if (!newProjectName.trim()) return
    try {
      await api.createProject(newProjectName.trim())
      setNewProjectName('')
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleJoin(id) {
    setError('')
    try {
      await api.joinProject(id)
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <section>
        <h2>My projects</h2>
        {myProjects.length === 0 && <p>You haven't joined any projects yet.</p>}
        <ul className="project-list">
          {myProjects.map((p) => (
            <li key={p.id}>
              <Link to={`/projects/${p.id}`}>{p.name}</Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>Create a project</h2>
        <form onSubmit={handleCreate} className="inline-form">
          <input
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="Project name"
          />
          <button type="submit" className="btn btn-primary">
            Create
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      <section>
        <h2>Other projects</h2>
        {otherProjects.length === 0 && <p>No other projects to join.</p>}
        <ul className="project-list">
          {otherProjects.map((p) => (
            <li key={p.id}>
              {p.name}
              <button className="btn btn-ghost" onClick={() => handleJoin(p.id)}>
                Join
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
