import { motion } from 'framer-motion'
import { AreaChart, Area, ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from 'recharts'

const threatTrend = [
  { name: '00:00', high: 10, medium: 6, low: 18 },
  { name: '02:00', high: 12, medium: 8, low: 16 },
  { name: '04:00', high: 14, medium: 10, low: 13 },
  { name: '06:00', high: 20, medium: 12, low: 10 },
  { name: '08:00', high: 18, medium: 16, low: 8 },
  { name: '10:00', high: 26, medium: 18, low: 9 },
]

const radarData = [
  { name: 'CPU', value: 78 },
  { name: 'Memory', value: 64 },
  { name: 'Network', value: 54 },
  { name: 'Process', value: 48 },
  { name: 'Threat', value: 82 },
]

const alertBreakdown = [
  { name: 'High', value: 15, color: '#ef4444' },
  { name: 'Medium', value: 31, color: '#f59e0b' },
  { name: 'Low', value: 86, color: '#22c55e' },
]

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <section className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Threat Level</p>
              <h2 className="mt-2 text-3xl font-semibold text-white">HIGH</h2>
            </div>
            <div className="rounded-3xl bg-rose-500/10 px-4 py-3 text-rose-300">Active ransomware detected</div>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {[
              { label: 'Events Today', value: '236', delta: '+35%' },
              { label: 'Processes Monitored', value: '124', delta: 'Active' },
              { label: 'Threat Confidence', value: '99.8%', delta: 'AI' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-3xl bg-slate-950/80 p-5">
                <p className="text-sm text-slate-500">{stat.label}</p>
                <p className="mt-2 text-2xl font-semibold text-white">{stat.value}</p>
                <p className="mt-1 text-sm text-slate-400">{stat.delta}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Prediction</p>
              <h2 className="mt-2 text-3xl font-semibold text-white">94.8%</h2>
            </div>
            <span className="rounded-3xl bg-cyan-500/10 px-4 py-3 text-cyan-300">LSTM-GNN</span>
          </div>
          <div className="space-y-4">
            {[
              { label: 'Confidence', value: '98%' },
              { label: 'Next prediction', value: '3 sec' },
              { label: 'Recommended action', value: 'Quarantine / rollback' },
            ].map((item) => (
              <div key={item.label} className="rounded-3xl bg-slate-950/80 p-4">
                <p className="text-sm text-slate-500">{item.label}</p>
                <p className="mt-1 text-lg font-semibold text-white">{item.value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30"
        >
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Live Event Trend</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">Attack timeline</h2>
            </div>
            <button className="rounded-2xl bg-slate-800 px-4 py-2 text-sm text-slate-200 hover:bg-slate-700">Refresh</button>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={threatTrend} margin={{ top: 10, right: 16, bottom: 10, left: -10 }}>
                <CartesianGrid stroke="#334155" strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: '#cbd5e1' }} />
                <YAxis tick={{ fill: '#cbd5e1' }} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: 16, borderColor: '#334155' }} />
                <Line type="monotone" dataKey="high" stroke="#ef4444" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="medium" stroke="#f59e0b" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="low" stroke="#22c55e" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.section>

        <section className="space-y-6">
          <div className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
            <p className="text-sm uppercase tracking-[0.35em] text-slate-500">Alert breakdown</p>
            <div className="mt-6 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={alertBreakdown} dataKey="value" nameKey="name" innerRadius={48} outerRadius={88} paddingAngle={4}>
                    {alertBreakdown.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
            <p className="text-sm uppercase tracking-[0.35em] text-slate-500">System health</p>
            <div className="mt-6 space-y-4">
              {radarData.map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-3xl bg-slate-950/80 px-4 py-4">
                  <span>{item.name}</span>
                  <span className="font-semibold text-white">{item.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
