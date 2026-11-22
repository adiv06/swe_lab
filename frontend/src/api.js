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
  createProject: (id, name, description = '') => request('/projects', {
    method: 'POST',
    body: { id, name, description },
  }),
  getProject: (id) => request(`/projects/${encodeURIComponent(id)}`),
  deleteProject: (id) => request(`/projects/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  joinProject: (id) => request(`/projects/${encodeURIComponent(id)}/join`, { method: 'POST' }),
  listHardware: () => request('/hardware'),
  checkoutHardware: (projectId, setId, quantity) => request(`/projects/${encodeURIComponent(projectId)}/hardware/${encodeURIComponent(setId)}/checkout`, { method: 'POST', body: { quantity } }),
  checkinHardware: (projectId, setId, quantity) => request(`/projects/${encodeURIComponent(projectId)}/hardware/${encodeURIComponent(setId)}/checkin`, { method: 'POST', body: { quantity } }),
  getInventory: () => request('/inventory'),
}
