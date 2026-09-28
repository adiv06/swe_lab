import { useState } from 'react'
import Button from './Button.jsx'

// A small "add a thing" form: one or more inputs plus a submit button. Used
// for both "create a project" and "register a hardware set". The caller owns
// validation/parsing inside `onSubmit` and can throw an Error to surface a
// message; fields reset automatically after a successful submit.
export default function InlineCreateForm({ fields, submitLabel, onSubmit }) {
  const initialValues = Object.fromEntries(fields.map((f) => [f.name, '']))
  const [values, setValues] = useState(initialValues)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      await onSubmit(values)
      setValues(initialValues)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="inline-form">
        {fields.map((field) => (
          <input
            key={field.name}
            type={field.type || 'text'}
            placeholder={field.placeholder}
            min={field.min}
            value={values[field.name]}
            onChange={(e) => setValues((v) => ({ ...v, [field.name]: e.target.value }))}
          />
        ))}
        <Button type="submit">{submitLabel}</Button>
      </form>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
