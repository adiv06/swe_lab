import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import { api } from '../mockApi.js'

export default function InventoryPage() {
  const [inventory, setInventory] = useState(null)
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const refresh = useCallback(async () => {
    setRefreshing(true)
    setError('')
    try {
      setInventory(await api.getInventory())
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const units = inventory?.units || []
  const availableUnits = units.filter((unit) => unit.status === 'available').length

  return (
    <div>
      <div className="inventory-heading">
        <div>
          <h1>Inventory</h1>
          <p className="project-description">Current availability and checkout holders.</p>
        </div>
        <Button variant="ghost" onClick={refresh} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {!inventory && !error && <p className="loading-text">Loading inventory...</p>}
      {inventory && (
        <>
          <div className="inventory-summary">
            <div><strong>{availableUnits} / {units.length}</strong><span>individual units available</span></div>
          </div>

          <section>
            <h2>Individual units</h2>
            {units.length === 0 ? <p className="form-note">No individual units have been added.</p> : (
              <div className="table-scroll">
                <table className="hw-table">
                  <thead><tr><th>Unit</th><th>Status</th><th>Checked out by</th><th>Project</th></tr></thead>
                  <tbody>
                    {units.map((unit) => (
                      <tr key={unit.id}>
                        <td><strong>{unit.name}</strong><small>{unit.id}</small></td>
                        <td><span className={`inventory-status ${unit.status === 'available' ? 'is-available' : 'is-allocated'}`}>{unit.status}</span></td>
                        <td>{unit.holder || '—'}</td>
                        <td>{unit.projectId ? <Link to={`/projects/${unit.projectId}`}>{unit.projectName || unit.projectId}</Link> : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
