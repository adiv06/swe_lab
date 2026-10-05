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
    const [mine, all] = await Promise.all([api.myProjects(), api.listProjects()])
    setMyProjects(mine)
    setOtherProjects(all.filter((p) => !p.isMember))
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleCreate({ name }) {
    if (!name.trim()) throw new Error('name is required')
    await api.createProject(name.trim())
    refresh()
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
      {error && <p className="error">{error}</p>}

      <section>
        <h2>My projects</h2>
        <ProjectList
          projects={myProjects}
          emptyText="You haven't joined any projects yet."
          renderItem={(p) => <Link to={`/projects/${p.id}`}>{p.name}</Link>}
        />
      </section>

      <section>
        <h2>Create a project</h2>
        <InlineCreateForm
          fields={[{ name: 'name', placeholder: 'Project name' }]}
          submitLabel="Create"
          onSubmit={handleCreate}
        />
      </section>

      <section>
        <h2>Other projects</h2>
        <ProjectList
          projects={otherProjects}
          emptyText="No other projects to join."
          renderItem={(p) => (
            <>
              {p.name}
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
