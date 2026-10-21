"""tables.py: the derived tables (run in the pinned python image from the lab root: scripts/lib.sh py).

out/sweep.csv        one row per sweep rep (raw values, no rounding)
out/sweep-table.txt  the sweep as the video shows it: killed k/5, max memory.peak of survivors (MiB, rounded down),
                     "limit reached" for killed cells (acc S4); <= 60 cells per row
out/who-killed.csv   who / exit / last log line / events / OOMKilled for s-stop, s-kill, r-oom
out/who-killed.txt   the same, aligned, <= 60 cells per row (last line cropped with "...")
out/nmt-table.txt    4 rows from the B-full NMT summary (committed, MiB, rounded): Java Heap, the two biggest
                     non-heap categories, everything else; plus the kernel-counted non-heap line
Every transform is named in the file's own header comment? No: the .txt files are panel text; the transforms are
listed here and in ACCURACY.md.
"""
import csv
import glob
import json
import os
import re

MIB = 2 ** 20


def res(cell):
    return [json.load(open(f)) for f in sorted(glob.glob(f'evidence/runs/{cell}/rep*/result.json'))]


def run(name):
    f = f'evidence/runs/{name}/result.json'
    return json.load(open(f)) if os.path.exists(f) else None


fx = json.load(open('out/fix.json')) if os.path.exists('out/fix.json') else {'P': '?'}
direct = json.load(open('out/direct.json')) if os.path.exists('out/direct.json') else {'direct_mb': '?'}
bug = json.load(open('out/bug.json'))['bug_variant'] if os.path.exists('out/bug.json') else 'a2'
P = fx['P']
LABEL = {
    'a': ('A', '-Xmx768m'),
    'a2': ('A2', '-Xms768m -Xmx768m'),
    'a85': ('A85', 'MaxRAMPercentage=85'),
    'a85s': ('A85s', 'Max+InitialRAMPercentage=85'),
    'd': ('D', '(no flag)'),
    'b': ('B', f'MaxRAMPercentage={P}'),
    'b-full': ('B-full', f'B, heap full from start'),
    'c': ('C', f"B-full + {direct['direct_mb']} MiB direct"),
}
CELLS = ['a', 'a2', 'a85', 'a85s', 'd', 'b', 'b-full', 'c']

# ---- sweep.csv ----
fields = ['cell', 'rep', 'java_tool_options', 'exit_code', 'oom_killed', 'outcome', 'oha_200', 'oha_errors',
          'memory_peak_bytes', 'probe_max_cgroup_mib', 'probe_max_heap_used_mib', 'probe_max_old_mib',
          'java_oome_lines', 'tail_s', 'other_cpu_pct_before', 'free_ram_gb_before', 'run_dir']
with open('out/sweep.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=fields)
    w.writeheader()
    for c in CELLS:
        for r in res(c):
            row = {k: r.get(k) for k in fields}
            row['oha_200'] = r['oha']['status'].get('200')
            row['oha_errors'] = sum(r['oha']['errors'].values())
            w.writerow(row)

# ---- sweep-table.txt ----
lines = [f"{'cell':<7}{'setting':<29}{'killed':<8}peak MiB"]
for c in CELLS:
    rs = res(c)
    if not rs:
        continue
    k = sum(r['outcome'] == 'killed' for r in rs)
    peaks = [r['memory_peak_bytes'] for r in rs if r['memory_peak_bytes']]
    oome = sum(r['outcome'] == 'java-oome' for r in rs)
    if k == len(rs):
        peak = 'limit reached'
    elif peaks:
        peak = str(max(peaks) // MIB)
    else:
        peak = '-'
    if oome:
        peak += f' ({oome} OOME)'
    name, flags = LABEL[c]
    lines.append(f"{name:<7}{flags:<29}{f'{k}/{len(rs)}':<8}{peak}")
open('out/sweep-table.txt', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

# ---- who-killed ----
rows = []
for who, name in (('docker stop', 's-stop'), ('docker kill', 's-kill'), ('kernel OOM', 'r-oom')):
    r = run(name)
    if not r:
        continue
    ev = [e for e in r['events'] if e['action'] in ('kill', 'oom')]
    sig = [e['attrs'].get('signal') for e in ev if e['action'] == 'kill']
    events = ('kill ' + ','.join(sig)) if sig else ('oom' if any(e['action'] == 'oom' for e in ev) else '-')
    last = r['last_line'] or ''
    last = last.split(' : ', 1)[1].strip() if ' : ' in last else last   # Spring's time/level/thread/logger prefix off
    rows.append({'who': who, 'exit': str(r['exit_code']), 'last log line': last, 'events': events,
                 'OOMKilled': str(r['oom_killed']).lower()})
with open('out/who-killed.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['who', 'exit', 'last log line', 'events', 'OOMKilled'])
    w.writeheader()
    w.writerows(rows)
W_LAST = 19


def crop(s, n):
    return s if len(s) <= n else s[:n - 3] + '...'


txt = [f"{'who':<13}{'exit':<6}{'last log line':<{W_LAST + 2}}{'events':<11}OOMKilled"]
for r in rows:
    txt.append(f"{r['who']:<13}{r['exit']:<6}{crop(r['last log line'], W_LAST):<{W_LAST + 2}}{r['events']:<11}{r['OOMKilled']}")
open('out/who-killed.txt', 'w', encoding='utf-8').write('\n'.join(txt) + '\n')

# ---- nmt-table ----
# each B-full rep's NMT summary (printed by -XX:+PrintNMTStatistics at exit) cut out of stdout.txt into nmt.txt, verbatim
for so in sorted(glob.glob('evidence/runs/b-full/rep*/stdout.txt')):
    keep, block = False, []
    for line in open(so, encoding='utf-8', errors='replace'):
        body = re.sub(r'^\S+Z ', '', line.rstrip('\n'))
        if body.startswith('Native Memory Tracking:'):
            keep = True
        if keep:
            block.append(line.rstrip('\n'))
    if block:
        open(so[:-len('stdout.txt')] + 'nmt.txt', 'w', encoding='utf-8').write('\n'.join(block) + '\n')
nmt_files = sorted(glob.glob('evidence/runs/b-full/rep*/stdout.txt'))
if nmt_files and 'non_heap_kernel_mib' in fx:
    t = open(nmt_files[0], encoding='utf-8', errors='replace').read()
    cats = {}
    # PrintNMTStatistics at exit prints bytes (jcmd would print KB)
    for name, com, kb in re.findall(r'-\s+([A-Za-z][A-Za-z ]+?) \(reserved=\d+(?:KB)?, committed=(\d+)(KB)?\)', t):
        cats[name.strip()] = int(com) * (1024 if kb else 1)
    m = re.search(r'Total: reserved=\d+(?:KB)?, committed=(\d+)(KB)?', t)
    total = int(m.group(1)) * (1024 if m.group(2) else 1)
    heap = cats.pop('Java Heap')
    top = sorted(cats.items(), key=lambda kv: -kv[1])[:2]
    rest = total - heap - sum(v for _, v in top)
    out = [f"{'NMT committed (B-full rep1)':<32}MiB",
           f"{'Java Heap':<32}{round(heap / MIB)}"]
    out += [f"{n:<32}{round(v / MIB)}" for n, v in top]
    out.append(f"{'everything else':<32}{round(rest / MIB)}")
    out.append(f"{'non-heap, kernel-counted (max)':<32}{round(fx['max_non_heap_kernel_mib'])}")
    open('out/nmt-table.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    json.dump({'source': nmt_files[0], 'categories_bytes': cats, 'heap_bytes': heap, 'total_bytes': total},
              open('out/nmt-split.json', 'w'), indent=1)
print(open('out/sweep-table.txt').read())
print(open('out/who-killed.txt').read() if rows else '(no who-killed runs yet)')
