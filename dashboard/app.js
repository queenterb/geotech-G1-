async function fetchAlerts() {
  const res = await fetch('/alerts?n=20');
  const data = await res.json();
  const container = document.getElementById('alerts');
  container.innerHTML = '';
  data.reverse().forEach((a, idx) => {
    const el = document.createElement('div');
    el.className = 'alert';
    el.innerHTML = `<strong>Alert ${idx+1}</strong> severity=${a.severity || 'N/A'} rule=${a.rule_name||a.rule||''}`;
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(a, null, 2);
    const btn = document.createElement('button');
    btn.textContent = 'Explain';
    btn.onclick = async () => {
      const r = await fetch('/explain', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(a)});
      const ex = await r.json();
      alert('Explanation:\n' + JSON.stringify(ex, null, 2));
    };
    el.appendChild(btn);
    el.appendChild(pre);
    container.appendChild(el);
  });
}

async function loadPlaybooks() {
  const res = await fetch('/playbooks');
  const p = await res.json();
  const sel = document.getElementById('playbooks');
  sel.innerHTML = '';
  p.forEach(x => {
    const o = document.createElement('option'); o.value = x; o.textContent = x; sel.appendChild(o);
  });
}

document.getElementById('refresh').onclick = fetchAlerts;
document.getElementById('runPlaybook').onclick = async () => {
  const sel = document.getElementById('playbooks');
  const playbook = sel.value;
  if (!playbook) { alert('Choose a playbook'); return; }
  const pid = prompt('PID to substitute (optional)');
  const body = { playbook, pid: pid ? Number(pid) : undefined, apply: false };
  const res = await fetch('/run_playbook', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const out = await res.json();
  alert('Playbook run result:\n' + JSON.stringify(out, null, 2));
};

loadPlaybooks();
fetchAlerts();
