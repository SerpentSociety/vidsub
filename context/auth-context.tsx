"use client"

import React, { createContext, useContext, useState, useEffect } from 'react'
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
  setIsAuthenticated: (value: boolean) => void
  setUser: (user: User | null) => void
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const initialAuthState: AuthContextType = {
  isAuthenticated: false,
  isLoading: true,
  user: null,
  setIsAuthenticated: () => {},
  setUser: () => {},
  login: async () => {},
  signup: async () => {},
  logout: () => {}
}

const AuthContext = createContext<AuthContextType>(initialAuthState)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const router = useRouter()

  useEffect(() => {
    const initAuth = async () => {
      const initialToken = localStorage.getItem('authToken')
      const initialUser = localStorage.getItem('user')
      
      if (initialToken && initialUser) {
        try {
          const data = await AuthService.validateToken(initialToken)
          setUser(data.user)
          localStorage.setItem('user', JSON.stringify(data.user))
          setIsAuthenticated(true)
        } catch (error) {
          console.error('Token validation failed:', error)
          localStorage.removeItem('authToken')
          localStorage.removeItem('user')
        }
      }
      
      setMounted(true)
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const data = await AuthService.login(email, password)
      setUser(data.user)
      localStorage.setItem('user', JSON.stringify(data.user))
      setIsAuthenticated(true)
      router.push('/dashboard')
    } catch (error: any) {
      throw error
    }
  }

  const signup = async (name: string, email: string, password: string) => {
    try {
      const data = await AuthService.signup(name, email, password)
      setUser(data.user)
      localStorage.setItem('user', JSON.stringify(data.user))
      setIsAuthenticated(true)
      router.push('/dashboard')
    } catch (error: any) {
      throw error
    }
  }

  const logout = async () => {
    try {
      await AuthService.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
      setUser(null)
      setIsAuthenticated(false)
      router.push('/login')
    }
  }

  if (!mounted) {
    return null
  }

  const value = {
    isAuthenticated,
    isLoading,
    user,
    setIsAuthenticated,
    setUser,
    login,
    signup,
    logout
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}