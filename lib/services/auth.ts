import axios, { AxiosError } from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5000/api'

interface User {
  id: string
  name: string
  email: string
}

interface AuthResponse {
  access_token: string
  user: User
  message: string
}

interface ValidationResponse {
  user: User
  message: string
}

interface ErrorResponse {
  error: string
  details?: string
}

interface UpdateProfileData {
  name?: string
  email?: string
  password?: string
}

const authApi = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: true
})

authApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

authApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
    }
    return Promise.reject(error)
  }
)

export class AuthService {
  static async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await authApi.post<AuthResponse>('/auth/login', {
        email,
        password
      })

      if (response.data.access_token) {
        localStorage.setItem('authToken', response.data.access_token)
      }

      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status
        const data = error.response?.data as ErrorResponse

        switch (status) {
          case 400:
            throw new Error(data?.error || 'Missing required fields')
          case 401:
            throw new Error(data?.error || 'Invalid email or password')
          case 404:
            throw new Error(data?.error || 'User not found')
          case 422:
            throw new Error('Validation failed')
          case 500:
            throw new Error('Server error. Please try again later.')
          default:
            throw new Error('An unexpected error occurred')
        }
      }
      throw new Error('Network error. Please check your connection.')
    }
  }

  static async signup(name: string, email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await authApi.post<AuthResponse>('/auth/signup', {
        name,
        email,
        password
      })

      if (response.data.access_token) {
        localStorage.setItem('authToken', response.data.access_token)
      }

      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status
        const data = error.response?.data as ErrorResponse

        switch (status) {
          case 400:
            throw new Error(data?.error || 'Missing required fields')
          case 409:
            throw new Error(data?.error || 'Email already registered')
          case 422:
            throw new Error('Validation failed')
          case 500:
            throw new Error('Server error. Please try again later.')
          default:
            throw new Error('An unexpected error occurred')
        }
      }
      throw new Error('Network error. Please check your connection.')
    }
  }

  static async validateToken(token: string): Promise<ValidationResponse> {
    try {
      const response = await authApi.get<ValidationResponse>('/auth/validate')
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status
        const data = error.response?.data as ErrorResponse

        switch (status) {
          case 401:
            throw new Error('Invalid or expired token')
          case 404:
            throw new Error('User not found')
          case 500:
            throw new Error('Server error. Please try again later.')
          default:
            throw new Error('Failed to validate token')
        }
      }
      throw new Error('Network error. Please check your connection.')
    }
  }

  static async logout(): Promise<void> {
    try {
      await authApi.post('/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('authToken')
      localStorage.removeItem('user')
    }
  }

  static async updateProfile(data: UpdateProfileData): Promise<ValidationResponse> {
    try {
      const response = await authApi.put<ValidationResponse>('/auth/update-profile', data)
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = error.response?.status
        const data = error.response?.data as ErrorResponse

        switch (status) {
          case 400:
            throw new Error(data?.error || 'Invalid input')
          case 401:
            throw new Error('Authentication required')
          case 404:
            throw new Error('User not found')
          case 409:
            throw new Error('Email already exists')
          case 422:
            throw new Error('Validation failed')
          case 500:
            throw new Error('Server error. Please try again later.')
          default:
            throw new Error('Failed to update profile')
        }
      }
      throw new Error('Network error. Please check your connection.')
    }
  }
}