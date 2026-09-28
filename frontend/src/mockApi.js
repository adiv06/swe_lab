// In-browser stand-in for the backend described in the spec. All state lives in
// localStorage so the app is fully usable without a server, while still enforcing
// the same allocation rule a real API would: available = total - allocated,
// checkout can't exceed available, check-in can't exceed what a project holds.

const DB_KEY = 'hw_allocator_db'
const SESSION_KEY = 'hw_allocator_session'

function uid() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`
}

function seedDb() {
  const db = {
    users: [],
    projects: [],
    hardwareSets: [
      { id: uid(), name: 'Arduino Kits', totalUnits: 10 },
      { id: uid(), name: 'Raspberry Pi Boards', totalUnits: 6 },
      { id: uid(), name: 'VR Headsets', totalUnits: 4 },
    ],
    allocations: [],
  }
  saveDb(db)
  return db
}

function loadDb() {
  try {
    const raw = localStorage.getItem(DB_KEY)
    if (raw) return JSON.parse(raw)
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

function allocatedTotal(db, hardwareSetId) {
  return db.allocations
    .filter((a) => a.hardwareSetId === hardwareSetId)
    .reduce((sum, a) => sum + a.quantity, 0)
}

function allocationFor(db, hardwareSetId, projectId) {
  return db.allocations.find((a) => a.hardwareSetId === hardwareSetId && a.projectId === projectId)
}

function serializeHardwareSet(db, hw) {
  const allocated = allocatedTotal(db, hw.id)
  return {
    id: hw.id,
    name: hw.name,
    totalUnits: hw.totalUnits,
    allocatedUnits: allocated,
    availableUnits: hw.totalUnits - allocated,
  }
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

export const api = {
  async register({ name, email, password }) {
    const db = loadDb()
    name = (name || '').trim()
    email = (email || '').trim().toLowerCase()
    if (!name || !email || !password) throw new Error('name, email, and password are required')
    if (db.users.some((u) => u.email === email)) {
      throw new Error('an account with this email already exists')
    }
    const user = { id: uid(), name, email, password }
    db.users.push(user)
    saveDb(db)
    localStorage.setItem(SESSION_KEY, user.id)
    return delay({ user: { id: user.id, name: user.name, email: user.email } })
  },

  async login({ email, password }) {
    const db = loadDb()
    email = (email || '').trim().toLowerCase()
    const user = db.users.find((u) => u.email === email && u.password === password)
    if (!user) throw new Error('invalid email or password')
    localStorage.setItem(SESSION_KEY, user.id)
    return delay({ user: { id: user.id, name: user.name, email: user.email } })
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
    return delay(user ? { id: user.id, name: user.name, email: user.email } : null)
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
    const db = loadDb()
    return delay(db.hardwareSets.map((hw) => serializeHardwareSet(db, hw)))
  },

  async createHardwareSet({ name, totalUnits }) {
    const db = loadDb()
    requireUser(db)
    name = (name || '').trim()
    if (!name || !Number.isInteger(totalUnits) || totalUnits < 0) {
      throw new Error('name and a non-negative integer total are required')
    }
    const hw = { id: uid(), name, totalUnits }
    db.hardwareSets.push(hw)
    saveDb(db)
    return delay(serializeHardwareSet(db, hw))
  },

  async listAllocations(hardwareSetId) {
    const db = loadDb()
    const hw = db.hardwareSets.find((h) => h.id === hardwareSetId)
    if (!hw) throw new Error('hardware set not found')
    const allocs = db.allocations.filter((a) => a.hardwareSetId === hardwareSetId && a.quantity > 0)
    return delay(
      allocs.map((a) => {
        const project = db.projects.find((p) => p.id === a.projectId)
        return {
          projectId: a.projectId,
          projectName: project ? project.name : 'Unknown project',
          quantity: a.quantity,
        }
      }),
    )
  },

  async checkout(hardwareSetId, projectId, quantity) {
    const db = loadDb()
    const user = requireUser(db)
    const hw = db.hardwareSets.find((h) => h.id === hardwareSetId)
    if (!hw) throw new Error('hardware set not found')
    const project = db.projects.find((p) => p.id === projectId)
    if (!project) throw new Error('project not found')
    if (!project.memberIds.includes(user.id)) throw new Error('you must be a member of this project')
    if (!Number.isInteger(quantity) || quantity <= 0) throw new Error('quantity must be a positive integer')

    const available = hw.totalUnits - allocatedTotal(db, hardwareSetId)
    if (quantity > available) throw new Error(`only ${available} unit(s) available`)

    const existing = allocationFor(db, hardwareSetId, projectId)
    if (existing) existing.quantity += quantity
    else db.allocations.push({ hardwareSetId, projectId, quantity })
    saveDb(db)
    return delay(serializeHardwareSet(db, hw))
  },

  async checkin(hardwareSetId, projectId, quantity) {
    const db = loadDb()
    const user = requireUser(db)
    const hw = db.hardwareSets.find((h) => h.id === hardwareSetId)
    if (!hw) throw new Error('hardware set not found')
    const project = db.projects.find((p) => p.id === projectId)
    if (!project) throw new Error('project not found')
    if (!project.memberIds.includes(user.id)) throw new Error('you must be a member of this project')
    if (!Number.isInteger(quantity) || quantity <= 0) throw new Error('quantity must be a positive integer')

    const existing = allocationFor(db, hardwareSetId, projectId)
    const allocatedToProject = existing ? existing.quantity : 0
    if (quantity > allocatedToProject) throw new Error(`this project only holds ${allocatedToProject} unit(s)`)

    existing.quantity -= quantity
    saveDb(db)
    return delay(serializeHardwareSet(db, hw))
  },
}
