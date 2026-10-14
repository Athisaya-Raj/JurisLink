import { createContext, useCallback, useContext, useState } from 'react'
import client from '../api/client.js'

const AuthContext = createContext(null)

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('jurislink_user') || 'null')
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readStoredUser)
  const [token, setToken] = useState(() => localStorage.getItem('jurislink_token'))

  const login = useCallback(async (username, password) => {
    const { data } = await client.post('/auth/login', { username, password })
    localStorage.setItem('jurislink_token', data.access_token)
    localStorage.setItem('jurislink_user', JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('jurislink_token')
    localStorage.removeItem('jurislink_user')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
