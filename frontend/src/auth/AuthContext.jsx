import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../mockApi.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  function setSession(userData) {
    setUser(userData)
  }

  async function logout() {
    try {
      await api.logout()
      setUser(null)
    } catch {
      // Keep the current session visible if server-side logout fails.
    }
  }

  return <AuthContext.Provider value={{ user, loading, setSession, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
