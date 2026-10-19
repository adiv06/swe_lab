import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import HardwareSetsTable from '../components/HardwareSetsTable.jsx'
import InlineCreateForm from '../components/InlineCreateForm.jsx'
import SectionBlock from '../components/SectionBlock.jsx'
import { api } from '../mockApi.js'

export default function ProjectPage() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [hardwareSets, setHardwareSets] = useState([])
  const [quantities, setQuantities] = useState({})
  const [error, setError] = useState('')

  async function refresh() {
    const [proj, sets] = await Promise.all([api.getProject(id), api.listHardwareSets()])
    setProject(proj)
    setHardwareSets(sets)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message))
  }, [id])

  async function handleCheckout(hwId) {
    setError('')
    const quantity = parseInt(quantities[hwId], 10)
    if (!quantity || quantity <= 0) return
    try {
      await api.checkout(hwId, quantity)
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
      await api.checkin(hwId, quantity)
      setQuantities((q) => ({ ...q, [hwId]: '' }))
      refresh()
    } catch (err) {
      setError(err.message)
    }
  }

  function handleQuantityChange(hwId, value) {
    setQuantities((q) => ({ ...q, [hwId]: value }))
  }

  async function handleCreateSet({ name, capacity, maxPerUser }) {
    const total = parseInt(capacity, 10)
    const cap = parseInt(maxPerUser, 10)
    if (!name.trim() || Number.isNaN(total) || total < 0 || Number.isNaN(cap) || cap < 1) {
      throw new Error('name, a non-negative capacity and a per-user cap of at least 1 are required')
    }
    await api.createHardwareSet({ name: name.trim(), capacity: total, maxPerUser: cap })
    refresh()
  }

  if (!project) return <p className="loading-text">Loading...</p>

  return (
    <div>
      <h1>{project.name}</h1>
      <p style={{ color: 'var(--text-dim)', marginTop: -8 }}>{project.memberIds.length} member(s)</p>
      <p className="project-description">
        {project.hardwareUnitId ? (
          <>
            Assigned hardware: {project.hardwareUnitName}<br />
            HW ID: <code>{project.hardwareUnitId}</code><br />
            Allocation ID: <code>{project.allocationId}</code>
          </>
        ) : 'No HW unit assigned to this project.'}
      </p>
      {error && <p className="error">{error}</p>}

      <SectionBlock title="Hardware sets">
        <HardwareSetsTable
          hardwareSets={hardwareSets}
          quantities={quantities}
          onQuantityChange={handleQuantityChange}
          onCheckout={handleCheckout}
          onCheckin={handleCheckin}
        />
      </SectionBlock>

      <SectionBlock title="Register a new hardware set">
        <InlineCreateForm
          fields={[
            { name: 'name', placeholder: 'Name' },
            { name: 'capacity', placeholder: 'Capacity', type: 'number', min: 0 },
            { name: 'maxPerUser', placeholder: 'Per-user cap', type: 'number', min: 1 },
          ]}
          submitLabel="Add hardware set"
          onSubmit={handleCreateSet}
        />
      </SectionBlock>
    </div>
  )
}
