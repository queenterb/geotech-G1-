import { useEffect, useState } from 'react'
import { createEventSocket } from '../services/socket'

export default function useLiveEvents() {
  const [events, setEvents] = useState([])

  useEffect(() => {
    const socket = createEventSocket((payload) => {
      setEvents((current) => [payload, ...current].slice(0, 30))
    })

    return () => {
      socket.close()
    }
  }, [])

  return events
}
