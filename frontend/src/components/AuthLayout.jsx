// Shared split-screen shell for the login/register pages: an animated branding
// panel on the left and a card slot on the right for page-specific form content.
export default function AuthLayout({ headline, description, features, orbitIcons, children }) {
  return (
    <div className="auth-split">
      <div className="auth-brand-panel">
        <div className="auth-grid-overlay" />

        <div className="auth-brand-top">
          <span className="brand-mark">HA</span> Hardware Allocator
        </div>

        <div className="auth-brand-mid">
          <h1>{headline}</h1>
          <p>{description}</p>

          <ul className="auth-feature-list">
            {features.map((feature) => (
              <li key={feature.text}>
                <span className="auth-feature-icon">{feature.icon}</span>
                {feature.text}
              </li>
            ))}
          </ul>
        </div>

        <div className="auth-orbit">
          {orbitIcons.map((icon, index) => (
            <div key={icon} className={`orbit-node n${index + 1}`}>
              {icon}
            </div>
          ))}
        </div>
      </div>

      <div className="auth-form-panel">
        <div className="auth-card">{children}</div>
      </div>
    </div>
  )
}
