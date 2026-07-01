import { Outlet, NavLink } from 'react-router-dom'

const navItems = [
  { label: 'Dashboard', path: '/' },
  { label: 'Live Events', path: '/live-events' },
  { label: 'Settings', path: '/settings' },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="grid min-h-screen grid-cols-[260px_1fr]">
        <aside className="border-r border-slate-800 bg-slate-900 p-6">
          <div className="mb-8 flex items-center gap-3 text-2xl font-semibold text-cyan-300">
            <div className="h-10 w-10 rounded-2xl bg-cyan-500/20" />
            CIS Dashboard
          </div>
          <nav className="space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  'block rounded-2xl px-4 py-3 text-sm font-semibold transition ' +
                  (isActive ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-300 hover:bg-slate-800')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <main className="p-6">
          <header className="mb-6 flex items-center justify-between rounded-3xl bg-slate-900/80 p-5 shadow-xl shadow-slate-950/20">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Causal Immune Sentinel</p>
              <h1 className="mt-2 text-2xl font-semibold text-white">Operations Center</h1>
            </div>
            <div className="inline-flex items-center gap-3 rounded-2xl bg-slate-950/70 px-4 py-3 text-slate-300">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" /> Live
            </div>
          </header>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
