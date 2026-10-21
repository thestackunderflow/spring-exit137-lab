"""analyze_run.py <run dir> <cell> <mode> <session> <compose file>: result.json from the raw files of one run.

Nothing is rounded here; tables round later and say so. Runs in the pinned python image (scripts/lib.sh py).
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

D, CELL, MODE, SESSION, CF = sys.argv[1:6]
OTHER = re.compile(r'mcp-canvas|reframe|ollama|llama|gemma|hikari|solidcraft|ogl|lc-')
TS = re.compile(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z) ?(.*)$')


def f(name):
    return os.path.join(D, name)


def read(name, default=''):
    try:
        with open(f(name), encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except FileNotFoundError:
        return default


def jread(name):
    t = read(name).strip()
    if not t:
        return None
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return None


def parse_ts(s):
    if not s or s.startswith('0001-'):
        return None
    m = re.match(r'(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?Z', s)
    frac = (m.group(2) or '0')[:6].ljust(6, '0')
    return datetime.strptime(m.group(1) + '.' + frac, '%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=timezone.utc)


def stats(name):
    t = read(name)
    m = re.search(r'free_ram_gb=([\d.]+)', t)
    cpu = 0.0
    for line in t.splitlines()[1:]:
        parts = line.split('\t')
        if len(parts) >= 2 and OTHER.search(parts[0]) and not parts[0].startswith('exit137'):
            try:
                cpu += float(parts[1].rstrip('%'))
            except ValueError:
                pass
    return (float(m.group(1)) if m else None), round(cpu, 1)


inspect = (jread('inspect.json') or [{}])[0]
state = inspect.get('State', {})
lines = []                       # (datetime, stream, text)
for stream in ('stdout', 'stderr'):
    for raw in read(stream + '.txt').splitlines():
        m = TS.match(raw)
        if m:
            lines.append((parse_ts(m.group(1)), stream, m.group(2)))
lines.sort(key=lambda x: x[0])
app_lines = [l for l in lines if not l[2].startswith('LAB: ')]
probe = [l[2] for l in lines if l[2].startswith('LAB: ')]


def probe_max(rx):
    vals = [int(m.group(1)) for p in probe for m in [re.search(rx, p)] if m]
    return max(vals) if vals else None


events = []
for raw in read('events.jsonl').splitlines():
    try:
        e = json.loads(raw)
    except json.JSONDecodeError:
        continue
    if e.get('Type') != 'container':
        continue
    action = e.get('Action', '').split(':')[0]
    attrs = {k: v for k, v in e.get('Actor', {}).get('Attributes', {}).items() if k in ('exitCode', 'signal')}
    events.append({'action': action, 'attrs': attrs, 'timeNano': e.get('timeNano')})
events.sort(key=lambda e: e['timeNano'] or 0)

oha_txt = read('oha.txt')
oha = {'status': {k: int(v) for k, v in re.findall(r'\[(\d{3})\] (\d+) responses', oha_txt)},
       'errors': {msg.strip(): int(n) for n, msg in re.findall(r'^\s*\[(\d+)\] (.+)$', oha_txt.split('Error distribution:')[1], re.M)}
       if 'Error distribution:' in oha_txt else {},
       'success_rate': (re.search(r'Success rate:\s*([\d.]+%)', oha_txt) or [None, None])[1]}

mem_ready = jread('mem-ready.json') or {}
mem_after = jread('mem-after.json')
state_after = jread('state-after.json')
exit_code = state.get('ExitCode')
oom = state.get('OOMKilled')
running_after = bool(state_after and state_after.get('Running'))
oome_lines = sum('OutOfMemoryError' in l[2] for l in lines)
finished = parse_ts(state.get('FinishedAt'))
last = app_lines[-1] if app_lines else None
tail = round((finished - last[0]).total_seconds(), 3) if finished and last else None

if exit_code == 137 and oom:
    outcome = 'killed'
elif oome_lines:
    outcome = 'java-oome'
elif running_after:
    outcome = 'survived'
else:
    outcome = 'other'

ram_b, cpu_b = stats('stats-before.txt')
ram_a, cpu_a = stats('stats-after.txt')
up = read('compose-up.txt')
exit_line = next((l.strip() for l in up.splitlines() if 'exited with code' in l), None)
peak = int(mem_after['memory.peak']) if mem_after and outcome == 'survived' and mem_after.get('memory.peak') else None
r = {
    'cell': CELL, 'rep': os.path.basename(D.rstrip('/')), 'run_dir': os.path.relpath(D, '/lab'), 'mode': MODE,
    'session': SESSION, 'compose_file': CF,
    'java_tool_options': next((e.split('=', 1)[1] for e in inspect.get('Config', {}).get('Env', [])
                               if e.startswith('JAVA_TOOL_OPTIONS=')), None),
    'exit_code': exit_code, 'oom_killed': oom, 'started_at': state.get('StartedAt'), 'finished_at': state.get('FinishedAt'),
    'running_after_load': running_after,
    'oom_killed_after_load': (state_after or {}).get('OOMKilled'),
    'outcome': outcome, 'limit_reached': outcome == 'killed',
    'events': events,
    'oha': oha, 'oha_cmd': read('cmd.txt').strip(),
    'mem_ready': mem_ready, 'mem_after': mem_after,
    'memory_peak_bytes': peak,
    'probe_max_cgroup_mib': probe_max(r'cgroup (\d+) MiB'), 'probe_max_heap_used_mib': probe_max(r'heap used (\d+) MiB'),
    'probe_max_old_mib': probe_max(r'old (\d+) MiB'), 'probe_samples': len(probe),
    'java_oome_lines': oome_lines,
    'last_line': last[2] if last else None, 'last_line_ts': last[0].isoformat() if last else None,
    'tail_s': tail,
    'compose_exit_line': exit_line, 'ps_status': read('ps.txt').strip(),
    'stop_seconds': float(read('stop-seconds.txt').strip()) if read('stop-seconds.txt').strip() else None,
    'running_10s_after_oome': read('running-10s-after.txt').strip() == 'true' if MODE == 'j' else None,
    'hold_status': read('hold-status.txt').strip() or None,
    'free_ram_gb_before': ram_b, 'free_ram_gb_after': ram_a, 'other_cpu_pct_before': cpu_b, 'other_cpu_pct_after': cpu_a,
    # disturbed: the host was short of RAM, or the other jobs used more than half the VM's 20 CPUs (re-run the cell)
    'disturbed': bool((ram_b is not None and ram_b < 4) or max(cpu_b, cpu_a) > 1000),
}
with open(f('result.json'), 'w', encoding='utf-8') as fh:
    json.dump(r, fh, indent=1)
print(f"{CELL} {r['rep']}: exit {exit_code} oom {oom} outcome {outcome} 2xx {oha['status'].get('200')} "
      f"peak {peak} probe_cg {r['probe_max_cgroup_mib']} tail {tail} other_cpu {cpu_b}/{cpu_a} ram {ram_b}")
