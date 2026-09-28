import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import Button from '../components/Button.jsx'
import InlineCreateForm from '../components/InlineCreateForm.jsx'
import { api } from '../mockApi.js'

export default function ProjectPage() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [hardwareSets, setHardwareSets] = useState([])
  const [myAllocations, setMyAllocations] = useState({})
  const [quantities, setQuantities] = useState({})
  const [error, setError] = useState('')

  async function refresh() {
    const [proj, sets] = await Promise.all([api.getProject(id), api.listHardwareSets()])
    setProject(proj)
    setHardwareSets(sets)
    const entries = await Promise.all(sets.map(async (hw) => [hw.id, await api.listAllocations(hw.id)]))
    const map = {}
    for (const [hwId, allocs] of entries) {
      const mine = allocs.find((a) => a.projectId === id)
      map[hwId] = mine ? mine.quantity : 0
    }
    setMyAllocations(map)
  }

  useEffect(() => {
    refresh()
  }, [id])

  async function handleCheckout(hwId) {
    setError('')
    const quantity = parseInt(quantities[hwId], 10)
    if (!quantity || quantity <= 0) return
    try {
      await api.checkout(hwId, id, quantity)
      setQuantities((q) => ({ ...q, [hwId]: '' }))
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleCheckin(hwId) {
    setError('')
    const quantity = parseInt(quantities[hwId], 10)
    if (!quantity || quantity <= 0) return
    try {
      await api.checkin(hwId, id, quantity)
      setQuantities((q) => ({ ...q, [hwId]: '' }))
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleCreateSet({ name, totalUnits }) {
    const total = parseInt(totalUnits, 10)
    if (!name.trim() || Number.isNaN(total) || total < 0) {
      throw new Error('name and a non-negative integer total are required')
    }
    await api.createHardwareSet({ name: name.trim(), totalUnits: total })
    refresh()
  }

  if (!project) return <p className="loading-text">Loading...</p>

  return (
    <div>
      <h1>{project.name}</h1>
      <p style={{ color: 'var(--text-dim)', marginTop: -8 }}>{project.memberIds.length} member(s)</p>
      {error && <p className="error">{error}</p>}

      <section>
        <h2>Hardware sets</h2>
        <table className="hw-table">
          <thead>
            <tr>
              <th>Set</th>
              <th>Total</th>
              <th>Available</th>
              <th>Held by this project</th>
              <th>Quantity</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {hardwareSets.map((hw) => (
              <tr key={hw.id}>
                <td>{hw.name}</td>
                <td>{hw.totalUnits}</td>
                <td>{hw.availableUnits}</td>
                <td>{myAllocations[hw.id] || 0}</td>
                <td>
                  <input
                    type="number"
                    min="1"
                    value={quantities[hw.id] || ''}
                    onChange={(e) => setQuantities((q) => ({ ...q, [hw.id]: e.target.value }))}
                  />
                </td>
                <td>
                  <Button onClick={() => handleCheckout(hw.id)}>Check out</Button>
                  <Button variant="ghost" onClick={() => handleCheckin(hw.id)}>
                    Check in
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Register a new hardware set</h2>
        <InlineCreateForm
          fields={[
            { name: 'name', placeholder: 'Name' },
            { name: 'totalUnits', placeholder: 'Total units', type: 'number', min: 0 },
          ]}
          submitLabel="Add hardware set"
          onSubmit={handleCreateSet}
        />
      </section>
    </div>
  )
}
