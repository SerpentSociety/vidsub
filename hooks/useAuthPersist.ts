import { useEffect } from 'react'
import { useAuth } from '@/context/auth-context'

export function useAuthPersist() {
  const { setUser, setIsAuthenticated } = useAuth()

  useEffect(() => {
    // Try to load auth state from localStorage immediately
    const token = localStorage.getItem('authToken')
    const savedUser = localStorage.getItem('user')

    if (token && savedUser) {
      try {
        const user = JSON.parse(savedUser)
        setUser(user)
        setIsAuthenticated(true)
      } catch (e) {
        localStorage.removeItem('authToken')
        localStorage.removeItem('user')
      }
    }
  }, [])
}