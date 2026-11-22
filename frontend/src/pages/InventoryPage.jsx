import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Button from '../components/Button.jsx'
import { api } from '../api.js'

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

  const sets = inventory?.sets || []

  return (
    <div>
      <div className="inventory-heading">
        <div>
          <h1>Inventory</h1>
          <p className="project-description">Availability of each hardware set and which projects hold units.</p>
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
            {sets.map((set) => (
              <div key={set.id}>
                <strong>{set.available} / {set.capacity}</strong>
                <span>{set.name} available</span>
              </div>
            ))}
          </div>

          {sets.map((set) => (
            <section key={set.id}>
              <h2>{set.name} <small className="form-note">({set.id})</small></h2>
              {set.holders.length === 0 ? <p className="form-note">No units checked out.</p> : (
                <div className="table-scroll">
                  <table className="hw-table">
                    <thead><tr><th>Project</th><th>Units checked out</th></tr></thead>
                    <tbody>
                      {set.holders.map((holder) => (
                        <tr key={holder.projectId}>
                          <td><Link to={`/projects/${holder.projectId}`}>{holder.projectName}</Link><small>{holder.projectId}</small></td>
                          <td>{holder.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ))}
        </>
      )}
    </div>
  )
}
