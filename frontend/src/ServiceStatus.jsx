export default function ServiceStatus({ status }) {
  const message = {
    checking: 'Checking database connection…',
    online: 'Database connected',
    offline: 'Database unavailable. Waiting to reconnect…',
  }[status]

  return (
    <div className={`service-status service-status-${status}`} role="status" aria-live="polite">
      <span className="service-status-dot" aria-hidden="true" />
      {message}
    </div>
  )
}
