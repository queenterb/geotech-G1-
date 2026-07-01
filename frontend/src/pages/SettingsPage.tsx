export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-slate-900/90 p-6 shadow-xl shadow-slate-950/30">
        <h2 className="text-2xl font-semibold text-white">System Settings</h2>
        <p className="mt-2 text-slate-400">Configure notifications, thresholds, and user settings.</p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {[
            { title: 'Dark Mode', description: 'Toggle dashboard theme mode.' },
            { title: 'AI Threshold', description: 'Adjust detection sensitivity.' },
            { title: 'Alert Threshold', description: 'Set when alerts are triggered.' },
            { title: 'Webhook Config', description: 'Send notifications to external systems.' },
          ].map((card) => (
            <div key={card.title} className="rounded-3xl bg-slate-950/80 p-5">
              <p className="text-sm text-slate-500">{card.title}</p>
              <p className="mt-3 text-slate-300">{card.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
