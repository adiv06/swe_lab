import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../mockApi.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.me().then((u) => {
      setUser(u)
      setLoading(false)
    })
  }, [])

  function setSession(userData) {
    setUser(userData)
  }

  function logout() {
    api.logout()
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, setSession, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
