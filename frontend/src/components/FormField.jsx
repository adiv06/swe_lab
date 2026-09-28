// Reusable labeled input: forwards any input prop (type, value, onChange,
// autoComplete, pattern, minLength, ...) straight through to the <input>.
export default function FormField({ id, label, ...inputProps }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} {...inputProps} />
    </div>
  )
}
