import { motion } from 'framer-motion'
import useLiveEvents from '../hooks/useLiveEvents'
import LiveStreamPlayer from '../components/LiveStreamPlayer'

export default function LiveEventsPage() {
  const events = useLiveEvents()

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_420px]">
        <section className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Live Events</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Real-Time Feed</h2>
            </div>
            <button className="rounded-2xl bg-cyan-500/15 px-4 py-2 text-sm text-cyan-300 hover:bg-cyan-500/25">Stream</button>
          </div>
          <div className="space-y-4">
            {events.map((event, index) => (
              <div key={event.id ?? index} className="rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-slate-500">{new Date(event.created_at ?? Date.now()).toLocaleTimeString()}</p>
                    <h3 className="mt-1 text-lg font-semibold text-white">{event.event_type ?? event.title ?? 'Event'}</h3>
                  </div>
                  <span className="rounded-full bg-slate-800 px-3 py-1 text-xs uppercase tracking-[0.25em] text-slate-300">
                    {event.severity ?? 'INFO'}
                  </span>
                </div>
                <div className="mt-3 text-slate-400 flex gap-4 items-start">
                  <p className="flex-1">{event.payload ?? event.detail}</p>
                  {event.payload && event.payload.thumbnail_base64 ? (
                    <img src={`data:image/jpeg;base64,${event.payload.thumbnail_base64}`} alt="thumb" className="w-28 rounded-md" />
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-slate-500">Status: <span className="text-slate-100">{event.status ?? 'Live'}</span></p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
          <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Live Stream</p>
          <div className="mt-6">
            <LiveStreamPlayer streamUrl={import.meta.env.VITE_STREAM_URL ?? 'http://localhost:8082/hls/stream.m3u8'} />
          </div>
        </section>
      </div>
    </motion.div>
  )
}
