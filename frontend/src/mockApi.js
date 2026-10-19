// All application records and sessions are served by the MongoDB-backed API.
async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((issue) => issue.msg).join(', ')
      : data.detail
    throw new Error(detail || 'Unable to reach the server')
  }
  return data
}

function serializeHardwareSet(hw) {
  return {
    id: hw.id,
    name: hw.name,
    capacity: hw.capacity,
    available: hw.available,
    maxPerUser: hw.max_per_user,
    held: hw.held,
  }
}

export const api = {
  register: (body) => request('/auth/register', { method: 'POST', body }),
  login: (body) => request('/auth/login', { method: 'POST', body }),
  logout: () => request('/auth/logout', { method: 'POST' }),

  async me() {
    const response = await fetch('/api/auth/me', { credentials: 'same-origin' })
    if (response.status === 401) return null
    if (!response.ok) throw new Error('Unable to reach the login service')
    return (await response.json()).user
  },

  listProjects: () => request('/projects'),
  async myProjects() {
    return (await request('/projects')).filter((project) => project.isMember)
  },
  createProject: (name, hardwareUnitId) => request('/projects', {
    method: 'POST',
    body: { name, hardware_unit_id: hardwareUnitId || null },
  }),
  getProject: (id) => request(`/projects/${encodeURIComponent(id)}`),
  joinProject: (id) => request(`/projects/${encodeURIComponent(id)}/join`, { method: 'POST' }),
  listAvailableUnits: () => request('/units/available'),

  async listHardwareSets() {
    return (await request('/hardware')).map(serializeHardwareSet)
  },
  async createHardwareSet({ name, capacity, maxPerUser }) {
    return serializeHardwareSet(await request('/hardware', {
      method: 'POST',
      body: { name, capacity, max_per_user: maxPerUser },
    }))
  },
  async listAllocations(hardwareSetId) {
    const allocations = await request(`/hardware/${encodeURIComponent(hardwareSetId)}/allocations`)
    return allocations.map((a) => ({ userId: a.user_id, quantity: a.quantity }))
  },
  async checkout(hardwareSetId, quantity) {
    return serializeHardwareSet(await request(`/hardware/${encodeURIComponent(hardwareSetId)}/checkout`, {
      method: 'POST', body: { quantity },
    }))
  },
  async checkin(hardwareSetId, quantity) {
    return serializeHardwareSet(await request(`/hardware/${encodeURIComponent(hardwareSetId)}/checkin`, {
      method: 'POST', body: { quantity },
    }))
  },
}
