import { Link } from 'react-router-dom'
import ServiceStatus from '../ServiceStatus.jsx'
import Button from './Button.jsx'

export default function AppHeader({ serviceStatus, userName, onLogout }) {
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        <span className="brand-mark">HA</span> Hardware Allocator
      </Link>
      <div className="topbar-actions">
        <ServiceStatus status={serviceStatus} />
        <span className="user-chip">{userName}</span>
        <Button variant="ghost" onClick={onLogout}>
          Log out
        </Button>
      </div>
    </header>
  )
}
