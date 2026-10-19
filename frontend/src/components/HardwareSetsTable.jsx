import Button from './Button.jsx'

export default function HardwareSetsTable({
  hardwareSets,
  quantities,
  onQuantityChange,
  onCheckout,
  onCheckin,
}) {
  return (
    <table className="hw-table">
      <thead>
        <tr>
          <th>Set</th>
          <th>Capacity</th>
          <th>Available</th>
          <th>Per-user cap</th>
          <th>Held by you</th>
          <th>Quantity</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {hardwareSets.map((hw) => (
          <tr key={hw.id}>
            <td>{hw.name}</td>
            <td>{hw.capacity}</td>
            <td>{hw.available}</td>
            <td>{hw.maxPerUser}</td>
            <td>{hw.held}</td>
            <td>
              <input
                type="number"
                min="1"
                value={quantities[hw.id] || ''}
                onChange={(e) => onQuantityChange(hw.id, e.target.value)}
              />
            </td>
            <td>
              <Button onClick={() => onCheckout(hw.id)}>Check out</Button>
              <Button variant="ghost" onClick={() => onCheckin(hw.id)}>
                Check in
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
