import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import ServiceStatus from '../ServiceStatus.jsx'

export default function PrivateRoute({ children, serviceStatus }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="loading-text">Loading...</p>
  if (!user) return <Navigate to="/login" replace />
  if (serviceStatus !== 'online') {
    return <div className="service-gate"><ServiceStatus status={serviceStatus} /></div>
  }
  return children
}
