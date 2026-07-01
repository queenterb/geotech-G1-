import { useEffect, useRef } from 'react'
import Hls from 'hls.js'

export default function LiveStreamPlayer({ streamUrl }: { streamUrl: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = streamUrl
    } else if (Hls.isSupported()) {
      const hls = new Hls()
      hls.loadSource(streamUrl)
      hls.attachMedia(video)
      return () => {
        hls.destroy()
      }
    }
  }, [streamUrl])

  return (
    <div className="w-full">
      <video ref={videoRef} controls muted className="w-full rounded-2xl bg-black" />
    </div>
  )
}
