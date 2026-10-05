// Thin wrapper around the .btn styles so every button in the app shares one
// definition of "primary" vs "ghost" instead of each page repeating class names.
export default function Button({ variant = 'primary', className = '', ...props }) {
  const variantClass = variant === 'ghost' ? 'btn-ghost' : 'btn-primary'
  return <button className={`btn ${variantClass} ${className}`.trim()} {...props} />
}
