import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import InlineCreateForm from '../components/InlineCreateForm.jsx'
import ProjectList from '../components/ProjectList.jsx'
import { api } from '../mockApi.js'

export default function DashboardPage() {
  const [myProjects, setMyProjects] = useState([])
  const [otherProjects, setOtherProjects] = useState([])
  const [error, setError] = useState('')

  async function refresh() {
    const all = await api.listProjects()
    setMyProjects(all.filter((p) => p.isMember))
    setOtherProjects(all.filter((p) => !p.isMember))
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message))
  }, [])

  async function handleCreate({ id, name }) {
    if (!/^[a-zA-Z0-9_-]{3,64}$/.test(id.trim())) throw new Error('Project ID must be 3–64 letters, numbers, underscores, or hyphens')
    if (!name.trim()) throw new Error('name is required')
    try {
      await api.createProject(id.trim(), name.trim())
    } catch (err) {
      await refresh()
      throw err
    }
    await refresh()
  }

  async function handleJoin(id) {
    setError('')
    try {
      await api.joinProject(id)
      await refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      {error && <p className="error">{error}</p>}

      <section>
        <h2>My projects</h2>
        <ProjectList
          projects={myProjects}
          emptyText="You haven't joined any projects yet."
          renderItem={(p) => (
            <>
              <Link to={`/projects/${p.id}`}>{p.name}</Link>
              <code>{p.id}</code>
            </>
          )}
        />
      </section>

      <section>
        <h2>Create a project</h2>
        <InlineCreateForm
          fields={[
            { name: 'id', placeholder: 'Project ID (unique)' },
            { name: 'name', placeholder: 'Project name' },
          ]}
          submitLabel="Create"
          onSubmit={handleCreate}
        />
      </section>

      <section className="project-join-section">
        <h2>Other projects</h2>
        <p className="form-note">Enter an existing project ID to join it.</p>
        <InlineCreateForm
          fields={[{ name: 'id', placeholder: 'Existing project ID' }]}
          submitLabel="Join project"
          onSubmit={async ({ id }) => { await api.joinProject(id.trim()); await refresh() }}
        />
        <ProjectList
          projects={otherProjects}
          emptyText="No other projects to join."
          renderItem={(p) => (
            <>
              {p.name} <code>{p.id}</code>
              <Button variant="ghost" onClick={() => handleJoin(p.id)}>
                Join
              </Button>
            </>
          )}
        />
      </section>
    </div>
  )
}
