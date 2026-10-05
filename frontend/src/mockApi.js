// Accounts and hardware go through the backend API (MongoDB). Projects are still
// an in-browser stand-in kept in localStorage.

const DB_KEY = 'hw_allocator_db'
const SESSION_KEY = 'hw_allocator_session'

function uid() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

function seedDb() {
  const db = {
    users: [],
    projects: [],
  }
  saveDb(db)
  return db
}

function loadDb() {
  try {
    const raw = localStorage.getItem(DB_KEY)
    if (raw) {
      const db = JSON.parse(raw)
      if (db.users?.some((user) => 'password' in user)) {
        db.users = db.users.map(({ password, ...user }) => user)
        saveDb(db)
      }
      return db
    }
  } catch {
    // corrupt or inaccessible storage falls through to reseeding
  }
  return seedDb()
}

function saveDb(db) {
  try {
    localStorage.setItem(DB_KEY, JSON.stringify(db))
  } catch {
    // storage unavailable (e.g. private browsing); state just won't persist
  }
}

function delay(value) {
  return new Promise((resolve) => setTimeout(() => resolve(value), 150))
}

function currentUserId() {
  try {
    return localStorage.getItem(SESSION_KEY)
  } catch {
    return null
  }
}

function requireUser(db) {
  const user = db.users.find((u) => u.id === currentUserId())
  if (!user) throw new Error('you must be logged in')
  return user
}

function serializeProject(project, userId) {
  return {
    id: project.id,
    name: project.name,
    creatorId: project.creatorId,
    memberIds: project.memberIds,
    isMember: userId ? project.memberIds.includes(userId) : false,
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
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

async function authRequest(path, payload) {
  const data = await request(`/auth/${path}`, { method: 'POST', body: payload })
  const db = loadDb()
  db.users = db.users.filter((user) => user.id !== data.user.id)
  db.users.push(data.user)
  saveDb(db)
  localStorage.setItem(SESSION_KEY, data.user.id)
  return data
}

export const api = {
  async register({ name, username, password }) {
    return authRequest('register', { name, username, password })
  },

  async login({ username, password }) {
    return authRequest('login', { username, password })
  },

  logout() {
    try {
      localStorage.removeItem(SESSION_KEY)
    } catch {
      // nothing to clean up if storage is unavailable
    }
  },

  async me() {
    const db = loadDb()
    const userId = currentUserId()
    const user = db.users.find((u) => u.id === userId)
    return delay(user ? { id: user.id, name: user.name, username: user.username } : null)
  },

  async listProjects() {
    const db = loadDb()
    const userId = currentUserId()
    return delay(db.projects.map((p) => serializeProject(p, userId)))
  },

  async myProjects() {
    const db = loadDb()
    const userId = currentUserId()
    if (!userId) return delay([])
    return delay(db.projects.filter((p) => p.memberIds.includes(userId)).map((p) => serializeProject(p, userId)))
  },

  async createProject(name) {
    const db = loadDb()
    const user = requireUser(db)
    name = (name || '').trim()
    if (!name) throw new Error('name is required')
    const project = { id: uid(), name, creatorId: user.id, memberIds: [user.id] }
    db.projects.push(project)
    saveDb(db)
    return delay(serializeProject(project, user.id))
  },

  async getProject(id) {
    const db = loadDb()
    const project = db.projects.find((p) => p.id === id)
    if (!project) throw new Error('project not found')
    return delay(serializeProject(project, currentUserId()))
  },

  async joinProject(id) {
    const db = loadDb()
    const user = requireUser(db)
    const project = db.projects.find((p) => p.id === id)
    if (!project) throw new Error('project not found')
    if (!project.memberIds.includes(user.id)) project.memberIds.push(user.id)
    saveDb(db)
    return delay(serializeProject(project, user.id))
  },

  async listHardwareSets() {
    const userId = currentUserId()
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
    const sets = await request(`/hardware${query}`)
    return sets.map(serializeHardwareSet)
  },

  async createHardwareSet({ name, capacity, maxPerUser }) {
    requireUser(loadDb())
    const hw = await request('/hardware', {
      method: 'POST',
      body: { name, capacity, max_per_user: maxPerUser },
    })
    return serializeHardwareSet(hw)
  },

  async listAllocations(hardwareSetId) {
    const allocations = await request(`/hardware/${encodeURIComponent(hardwareSetId)}/allocations`)
    return allocations.map((a) => ({ userId: a.user_id, quantity: a.quantity }))
  },

  async checkout(hardwareSetId, quantity) {
    const user = requireUser(loadDb())
    const hw = await request(`/hardware/${encodeURIComponent(hardwareSetId)}/checkout`, {
      method: 'POST',
      body: { user_id: user.id, quantity },
    })
    return serializeHardwareSet(hw)
  },

  async checkin(hardwareSetId, quantity) {
    const user = requireUser(loadDb())
    const hw = await request(`/hardware/${encodeURIComponent(hardwareSetId)}/checkin`, {
      method: 'POST',
      body: { user_id: user.id, quantity },
    })
    return serializeHardwareSet(hw)
  },
}
