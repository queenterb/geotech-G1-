import axios from 'axios'

const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

export const apiClient = axios.create({
  baseURL: apiBase,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function fetchAlerts(limit = 20) {
  const response = await apiClient.get('/alerts', { params: { limit } })
  return response.data
}

export async function createAlert(alert) {
  const response = await apiClient.post('/alerts', alert)
  return response.data
}

export async function loginUser(data) {
  const response = await apiClient.post('/auth/token', new URLSearchParams(data), {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  })
  return response.data
}
