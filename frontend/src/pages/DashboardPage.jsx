import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import InlineCreateForm from '../components/InlineCreateForm.jsx'
import ProjectList from '../components/ProjectList.jsx'
import { api } from '../mockApi.js'

export default function DashboardPage() {
  const [myProjects, setMyProjects] = useState([])
  const [otherProjects, setOtherProjects] = useState([])
  const [availableUnits, setAvailableUnits] = useState([])
  const [unitsLoaded, setUnitsLoaded] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    const [all, units] = await Promise.all([api.listProjects(), api.listAvailableUnits()])
    setMyProjects(all.filter((p) => p.isMember))
    setOtherProjects(all.filter((p) => !p.isMember))
    setAvailableUnits(units)
    setUnitsLoaded(true)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message))
  }, [])

  async function handleCreate({ name, hardwareUnitId }) {
    if (!name.trim()) throw new Error('name is required')
    try {
      await api.createProject(name.trim(), hardwareUnitId)
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
              <span className="project-hw-summary">
                {p.hardwareUnitId ? `HW ID: ${p.hardwareUnitId}` : 'No HW assigned'}
              </span>
            </>
          )}
        />
      </section>

      <section>
        <h2>Create a project</h2>
        <InlineCreateForm
          fields={[
            { name: 'name', placeholder: 'Project name' },
            {
              name: 'hardwareUnitId',
              placeholder: !unitsLoaded
                ? 'Checking hardware...'
                : availableUnits.length === 0
                  ? 'No HW available'
                  : 'Request a hardware unit (optional)',
              disabled: availableUnits.length === 0,
              options: availableUnits.map((unit) => ({ value: unit.id, label: unit.name })),
            },
          ]}
          submitLabel="Create"
          onSubmit={handleCreate}
        />
        {unitsLoaded && availableUnits.length === 0 && (
          <p className="form-note">No HW available right now. You can still create a project.</p>
        )}
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
