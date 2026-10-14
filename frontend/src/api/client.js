import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// Attach the JWT to every request.
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('jurislink_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Centralised handling of 401 (expired/invalid token) and 403 (forbidden).
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const path = window.location.pathname
    if (status === 401 && !path.startsWith('/login')) {
      localStorage.removeItem('jurislink_token')
      localStorage.removeItem('jurislink_user')
      window.location.href = '/login'
    } else if (status === 403 && !path.startsWith('/login') && !path.startsWith('/unauthorized')) {
      window.location.href = '/unauthorized'
    }
    return Promise.reject(error)
  },
)

export function apiErrorMessage(error, fallback = 'Something went wrong.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail.map((d) => d.msg || d).join(', ')
  }
  return error?.message || fallback
}

export default client
