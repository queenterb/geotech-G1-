export function createEventSocket(onMessage) {
  const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'
  const url = baseUrl.replace(/^http/, 'ws').replace(/\/api$/, '/ws/events')
  const socket = new WebSocket(url)

  socket.addEventListener('open', () => {
    console.log('WebSocket connected')
  })

  socket.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data)
      onMessage(payload)
    } catch {
      console.warn('Invalid event payload', event.data)
    }
  })

  socket.addEventListener('close', () => {
    console.log('WebSocket disconnected')
  })

  return socket
}
