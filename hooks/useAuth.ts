"use client"

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { AuthService } from '@/lib/services/auth'

interface User {
  id: string
  name: string
  email: string
}

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

export function useAuth(): AuthContextType {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const router = useRouter()

  useEffect(() => {
    const validateSession = async () => {
      const token = localStorage.getItem('authToken')
      
      if (!token) {
        setIsAuthenticated(false)
        setUser(null)
        setIsLoading(false)
        router.push('/login')
        return
      }

      try {
        const data = await AuthService.validateToken(token)
        setUser(data.user)
        setIsAuthenticated(true)
      } catch (error) {
        console.error('Token validation error:', error)
        logout()
      } finally {
        setIsLoading(false)
      }
    }

    if (typeof window !== 'undefined') {
      validateSession()
    }
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const data = await AuthService.login(email, password)
      setUser(data.user)
      setIsAuthenticated(true)
      router.push('/dashboard')
    } catch (error) {
      console.error('Login error:', error)
      if (error instanceof Error) {
        throw error
      } else {
        throw new Error('An unexpected error occurred during login')
      }
    }
  }

  const signup = async (name: string, email: string, password: string) => {
    try {
      const data = await AuthService.signup(name, email, password)
      setUser(data.user)
      setIsAuthenticated(true)
      router.push('/dashboard')
    } catch (error) {
      console.error('Signup error:', error)
      if (error instanceof Error) {
        throw error
      } else {
        throw new Error('An unexpected error occurred during signup')
      }
    }
  }

  const logout = () => {
    if (typeof window !== 'undefined') {
      AuthService.logout().then(() => {
        setUser(null)
        setIsAuthenticated(false)
        router.push('/login')
      }).catch((error) => {
        console.error('Logout error:', error)
        // Still clear local state even if server logout fails
        setUser(null)
        setIsAuthenticated(false)
        router.push('/login')
      })
    }
  }

  return { 
    isAuthenticated, 
    isLoading,
    user,
    login, 
    signup, 
    logout 
  }
}