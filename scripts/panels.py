"""panels.py: the video's panel text, cut from evidence/ and out/ (run after tables.py, in the pinned python image).

Every panel line is a verbatim substring of its source file (T14 checks it). Transforms: leading whitespace and the
`docker logs --timestamps` prefix are dropped; the compact `state-after.json` is re-indented to
`state-after.pretty.json` (json.dumps, indent 4, same keys and values). Writes video/*.txt + video/panel-sources.json.
"""
import json
import os
import re

os.makedirs('video', exist_ok=True)
SRC = {}


def rd(p):
    return open(p, encoding='utf-8', errors='replace').read()


def find(path, pattern):
    """the first line of path matching pattern, stripped, without the docker timestamp prefix"""
    for line in rd(path).splitlines():
        body = re.sub(r'^\S+Z ', '', line).strip()
        body = re.sub(r'^\x1b\[K', '', body.replace('\r', '')).strip()
        if re.search(pattern, body):
            return body
    raise SystemExit(f'{path}: no line matches {pattern!r}')


def panel(name, lines, sources, max_cells=60):
    open(f'video/{name}', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    SRC[name] = {'sources': sources, 'max_cells': max_cells}


R = 'evidence/runs/r-oom/'
P = 'evidence/runs/r-proof/'
st = json.loads(rd(P + 'state-after.json'))
open(P + 'state-after.pretty.json', 'w', encoding='utf-8').write(json.dumps(st, indent=4) + '\n')

panel('ch0-terminal.txt', [
    find(R + 'compose-up.txt', r'app-1 exited with code 137'),
    find(R + 'ps.txt', r'Exited \(137\)'),
    find(R + 'inspect.json', r'"ExitCode": 137'),
    find(R + 'inspect.json', r'"OOMKilled": true'),
], [R + 'compose-up.txt', R + 'ps.txt', R + 'inspect.json'])

panel('hook-callout.txt', [find(R + 'stderr.txt', r'^Picked up JAVA_TOOL_OPTIONS')], [R + 'stderr.txt'])

keys = ['Status', 'Running', 'OOMKilled', 'Pid', 'ExitCode', 'Error', 'StartedAt', 'FinishedAt']
panel('ch2-inspect-state.txt', [find(R + 'inspect.json', rf'^"{k}": ') for k in keys], [R + 'inspect.json'])

panel('ch3-who-killed.txt', rd('out/who-killed.txt').rstrip('\n').splitlines(), ['out/who-killed.txt'])
panel('ch4-nmt-table.txt', rd('out/nmt-table.txt').rstrip('\n').splitlines(), ['out/nmt-table.txt'])

panel('ch5-showsettings.txt', [
    find('evidence/t4/b-system.txt', r'^Provider: cgroupv2'),
    find('evidence/t4/b-system.txt', r'^Memory Limit: '),
    find('evidence/t4/b-flags.txt', r'^size_t MaxHeapSize\s').split('{')[0].rstrip(),
    find('evidence/t4/b-flags.txt', r'^bool UseSerialGC\s').split('{')[0].rstrip(),
], ['evidence/t4/b-system.txt', 'evidence/t4/b-flags.txt'])

panel('ch5-java-oome.txt', [find('evidence/runs/j/stdout.txt', r'^java\.lang\.OutOfMemoryError: Java heap space')],
      ['evidence/runs/j/stdout.txt'])

panel('ch6-proof.txt', [
    find(P + 'oha.txt', r'\[200\] \d+ responses'),
    find(P + 'state-after.pretty.json', r'^"Running": true'),
    find(P + 'state-after.pretty.json', r'^"OOMKilled": false'),
], [P + 'oha.txt', P + 'state-after.pretty.json'])

panel('ch6-sweep-table.txt', rd('out/sweep-table.txt').rstrip('\n').splitlines(), ['out/sweep-table.txt'])

if os.path.exists('evidence/t10/dmesg-oom.txt'):
    k = find('evidence/t10/dmesg-oom.txt', r'Memory cgroup out of memory: Killed process \d+ \(java\)')
    panel('description-dmesg.txt', [re.search(r'Memory cgroup out of memory: Killed process \d+ \(java\)', k).group(0)],
          ['evidence/t10/dmesg-oom.txt'])

json.dump(SRC, open('video/panel-sources.json', 'w'), indent=1)
for n in SRC:
    print(f'--- {n}')
    print(rd('video/' + n), end='')
