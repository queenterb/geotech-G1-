import { useQuery } from '@tanstack/react-query'
import { fetchAlerts } from '../services/api'

export default function useAlerts(limit = 20) {
  return useQuery(['alerts', limit], () => fetchAlerts(limit), {
    staleTime: 5000,
    refetchInterval: 5000,
  })
}
