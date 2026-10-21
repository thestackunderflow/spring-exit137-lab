"""T0-T12: what the evidence must show (PLAN rev. 2, section 3.7). Written before any run; red until the runs exist.

Every test reads only files the scripts wrote (out/, evidence/, load.env) and the pinned files (scripts/lib.sh,
compose.*.yaml). Run inside the pinned python image: bash tests/run-tests.sh
"""
import csv
import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 805306368            # 768 MiB
MIB = 1024 * 1024
REPS = 5


def p(*parts):
    return os.path.join(ROOT, *parts)


def jload(*parts):
    with open(p(*parts), encoding='utf-8') as f:
        return json.load(f)


def text(*parts):
    with open(p(*parts), encoding='utf-8', errors='replace') as f:
        return f.read()


def results(cell):
    """result.json of every rep of a sweep cell, in rep order."""
    files = sorted(glob.glob(p('evidence', 'runs', cell, 'rep*', 'result.json')))
    out = []
    for f in files:
        with open(f, encoding='utf-8') as fh:
            out.append(json.load(fh))
    return out


def run(name):
    return jload('evidence', 'runs', name, 'result.json')


def killed(r):
    return r['exit_code'] == 137 and r['oom_killed'] is True


def survived(r):
    return r['running_after_load'] is True and r['oom_killed'] is False and r['java_oome_lines'] == 0


def actions(r):
    return [e['action'] for e in r['events']]


def bug_cell():
    return jload('out', 'bug.json')['bug_variant']


def pinned_images():
    lib = text('scripts', 'lib.sh')
    return dict(re.findall(r'^\w+_IMAGE=([^@\s]+)@(sha256:[0-9a-f]{64})', lib, re.M))


class T0Environment(unittest.TestCase):
    def test_env_recorded(self):
        env = jload('out', 'env.json')
        for k in ('docker_server_version', 'docker_desktop', 'containerd_version', 'kernel', 'vm_memtotal_kb',
                  'vm_swaptotal_kb', 'cgroup_fs', 'docker_info_warnings', 'lscpu_model', 'ncpu', 'recorded_utc'):
            self.assertIn(k, env, k)
        self.assertNotIn('No swap limit support', ' '.join(env['docker_info_warnings']))

    def test_images_resolve_to_pinned_digests(self):
        env = jload('out', 'env.json')
        pins = pinned_images()
        self.assertGreaterEqual(len(pins), 5)
        for ref, digest in pins.items():
            self.assertEqual(env['images'][ref]['digest'], digest, ref)


class T1Cgroup(unittest.TestCase):
    def test_cgroup_v2_and_limits_in_every_run(self):
        self.assertEqual(jload('out', 'basics.json')['cgroup_fs'], 'cgroup2fs')
        files = glob.glob(p('evidence', 'runs', '**', 'result.json'), recursive=True)
        self.assertGreater(len(files), 30)
        for f in files:
            with open(f, encoding='utf-8') as fh:
                r = json.load(fh)
            ready = r['mem_ready']
            self.assertEqual(ready['memory.max'], str(LIMIT), f)
            self.assertIn('memory.peak', ready, f)
            want_swap = str(LIMIT) if r['cell'] == 'a-swap' else '0'
            self.assertEqual(ready['memory.swap.max'], want_swap, f)


class T2Versions(unittest.TestCase):
    def test_starter_webmvc_not_web(self):
        tree = text('out', 'dependency-tree.txt')
        self.assertIn('spring-boot-starter-webmvc:jar:4.1.1', tree)
        self.assertNotRegex(tree, r'spring-boot-starter-web:jar')

    def test_startup_log_versions(self):
        log = text('evidence', 'runs', 'r-oom', 'stdout.txt')
        self.assertIn(':: Spring Boot ::', log)
        self.assertIn('(v4.1.1)', log)
        self.assertRegex(log, r'using Java 21\.0\.12\.1')


class T3Calibration(unittest.TestCase):
    def test_load_env_frozen(self):
        env = dict(l.split('=', 1) for l in text('load.env').split() if '=' in l)
        for k in ('K', 'MB', 'N', 'C'):
            self.assertIn(k, env)

    def test_gc_is_serial(self):
        self.assertEqual(jload('out', 'bug.json')['gc'], 'serial')

    def test_bug_cell_killed_5_of_5(self):
        bug = jload('out', 'bug.json')
        self.assertIn(bug['bug_variant'], ('a', 'a2'))
        if bug['bug_variant'] == 'a2':                     # stop rule: A first, then A2
            self.assertLess(sum(killed(r) for r in results('a')), REPS)
        rs = results(bug['bug_variant'])
        self.assertEqual(len(rs), REPS)
        self.assertTrue(all(killed(r) for r in rs), [(r['exit_code'], r['oom_killed']) for r in rs])

    def test_d_outcome_recorded(self):
        rs = results('d')
        self.assertEqual(len(rs), REPS)
        for r in rs:
            self.assertIn(r['outcome'], ('survived', 'java-oome', 'killed'))


class T4Ergonomics(unittest.TestCase):
    def test_container_seen(self):
        s = text('evidence', 't4', 'a2-system.txt')
        self.assertIn('Provider: cgroupv2', s)
        self.assertIn('Memory Limit: 768.00M', s)

    def test_max_heap_size_per_variant(self):
        b = jload('out', 'basics.json')['max_heap_size']
        self.assertEqual(b['a'], LIMIT)
        self.assertEqual(b['a2'], LIMIT)
        self.assertEqual(b['d'], LIMIT // 4)
        P = jload('out', 'fix.json')['P']
        self.assertLessEqual(abs(b['b'] - LIMIT * P / 100), 2 * MIB)   # aligned down to the heap alignment

    def test_serial_gc_selected(self):
        self.assertTrue(all(jload('out', 'basics.json')['use_serial_gc'].values()))


class T5Fix(unittest.TestCase):
    def test_p_from_kernel_counted_non_heap(self):
        fx = jload('out', 'fix.json')
        P = fx['P']
        self.assertEqual(P % 5, 0)
        nh = max(fx['non_heap_kernel_mib'])
        self.assertLessEqual(P / 100 * 768 + nh + 76.8, 768)
        self.assertGreater((P + 5) / 100 * 768 + nh + 76.8, 768)   # the largest such multiple of 5

    def test_b_full_survives_5_of_5_under_90_percent(self):
        rs = results('b-full')
        self.assertEqual(len(rs), REPS)
        for r in rs:
            self.assertTrue(survived(r), r['run_dir'])
            self.assertLessEqual(r['memory_peak_bytes'], 0.9 * LIMIT, r['run_dir'])

    def test_b_survives_5_of_5(self):
        rs = results('b')
        self.assertEqual(len(rs), REPS)
        self.assertTrue(all(survived(r) for r in rs))

    def test_nmt_split_captured(self):
        self.assertTrue(glob.glob(p('evidence', 'runs', 'b-full', 'rep*', 'nmt.txt')))
        t = text('out', 'nmt-table.txt')
        self.assertIn('Java Heap', t)
        for line in t.splitlines():
            self.assertLessEqual(len(line), 60, line)


class T6Swap(unittest.TestCase):
    def test_swap_cell_recorded(self):
        r = run('a-swap')
        self.assertEqual(r['mem_ready']['memory.swap.max'], str(LIMIT))
        self.assertIn('Memory & Swap Limit: 1.50G', text('evidence', 't4', 'a-swap-system.txt'))
        self.assertIn(r['outcome'], ('survived', 'killed', 'java-oome'))


class T7CardIsTheFileTheRunRead(unittest.TestCase):
    def check(self, name, compose_file):
        first = text('evidence', 'runs', name, 'stderr.txt').splitlines()[0]
        first = re.sub(r'^\S+Z ', '', first)         # docker logs --timestamps prefix
        compose = text(compose_file)
        value = re.search(r'JAVA_TOOL_OPTIONS: "([^"]+)"', compose).group(1)
        self.assertEqual(first, 'Picked up JAVA_TOOL_OPTIONS: ' + value)
        labels = jload('evidence', 'runs', name, 'inspect.json')[0]['Config']['Labels']
        self.assertTrue(labels['com.docker.compose.project.config_files'].endswith(compose_file))

    def test_r_oom(self):
        self.check('r-oom', 'compose.bug.yaml')

    def test_r_proof(self):
        self.check('r-proof', 'compose.fix.yaml')


class T8WhoKilled(unittest.TestCase):
    def test_r_oom(self):
        r = run('r-oom')
        self.assertTrue(killed(r))
        a = actions(r)
        self.assertIn('oom', a)
        self.assertIn('die', a)
        self.assertNotIn('kill', a)
        log = text('evidence', 'runs', 'r-oom', 'stdout.txt') + text('evidence', 'runs', 'r-oom', 'stderr.txt')
        for bad in ('ERROR', 'OutOfMemoryError', 'Commencing graceful shutdown'):
            self.assertNotIn(bad, log)
        self.assertIn('app-1 exited with code 137', text('evidence', 'runs', 'r-oom', 'compose-up.txt'))
        self.assertIn('Exited (137)', text('evidence', 'runs', 'r-oom', 'ps.txt'))

    def test_s_stop(self):
        r = run('s-stop')
        self.assertEqual((r['exit_code'], r['oom_killed']), (137, False))
        self.assertIn('Commencing graceful shutdown', text('evidence', 'runs', 's-stop', 'stdout.txt'))
        kills = [e['attrs'].get('signal') for e in r['events'] if e['action'] == 'kill']
        self.assertEqual(kills, ['15', '9'])
        self.assertNotIn('oom', actions(r))
        self.assertAlmostEqual(r['stop_seconds'], 10, delta=1)

    def test_s_kill(self):
        r = run('s-kill')
        self.assertEqual((r['exit_code'], r['oom_killed']), (137, False))
        kills = [e['attrs'].get('signal') for e in r['events'] if e['action'] == 'kill']
        self.assertEqual(kills, ['9'])
        self.assertNotIn('Commencing graceful shutdown', text('evidence', 'runs', 's-kill', 'stdout.txt'))

    def test_who_killed_table(self):
        with open(p('out', 'who-killed.csv'), encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r['who'] for r in rows], ['docker stop', 'docker kill', 'kernel OOM'])
        self.assertEqual({r['exit'] for r in rows}, {'137'})
        self.assertEqual([r['OOMKilled'] for r in rows], ['false', 'false', 'true'])
        for line in text('out', 'who-killed.txt').splitlines():
            self.assertLessEqual(len(line), 60, line)


class T8bTail(unittest.TestCase):
    def test_tail_recorded(self):
        r = run('r-oom')
        self.assertIsNotNone(r['tail_s'])
        self.assertGreater(r['tail_s'], 0)


class T9EventOrder(unittest.TestCase):
    def test_oom_before_die(self):
        a = actions(run('r-oom'))
        self.assertLess(a.index('oom'), a.index('die'))

    def test_stop_order(self):
        a = [(e['action'], e['attrs'].get('signal')) for e in run('s-stop')['events'] if e['action'] in ('kill', 'die')]
        self.assertEqual(a, [('kill', '15'), ('kill', '9'), ('die', None)])

    def test_every_bug_rep_has_oom_and_no_kill(self):
        for r in results(bug_cell()):
            self.assertIn('oom', actions(r))
            self.assertNotIn('kill', actions(r))


class T10Dmesg(unittest.TestCase):
    def test_kernel_line_if_captured(self):
        f = p('evidence', 't10', 'dmesg-oom.txt')
        if not os.path.exists(f):
            self.skipTest('T10 optional: dmesg not captured')
        self.assertRegex(text('evidence', 't10', 'dmesg-oom.txt'), r'Memory cgroup out of memory: Killed process \d+ \(java\)')


class T11JavaOome(unittest.TestCase):
    def test_j_logs_and_keeps_running(self):
        r = run('j')
        log = text('evidence', 'runs', 'j', 'stdout.txt') + text('evidence', 'runs', 'j', 'stderr.txt')
        self.assertIn('java.lang.OutOfMemoryError: Java heap space', log)
        self.assertTrue(r['running_10s_after_oome'])
        self.assertFalse(r['oom_killed'])

    def test_j2_exits_3(self):
        r = run('j2')
        self.assertEqual(r['exit_code'], 3)
        self.assertFalse(r['oom_killed'])
        self.assertIn('Terminating due to java.lang.OutOfMemoryError: Java heap space',
                      text('evidence', 'runs', 'j2', 'stdout.txt'))


class T12Proof(unittest.TestCase):
    def test_r_proof(self):
        r = run('r-proof')
        load = dict(l.split('=', 1) for l in text('load.env').split() if '=' in l)
        self.assertEqual(r['oha']['status'].get('200'), int(load['N']))
        self.assertEqual(r['java_oome_lines'], 0)
        self.assertTrue(r['running_after_load'])
        self.assertFalse(r['oom_killed_after_load'])
        self.assertLess(r['memory_peak_bytes'], LIMIT)
        self.assertEqual(r['exit_code'], 143)
        self.assertIn('Graceful shutdown complete', text('evidence', 'runs', 'r-proof', 'stdout.txt'))
        self.assertEqual(r['session'], run('r-oom')['session'])


class SweepTable(unittest.TestCase):
    def test_sweep_csv_has_every_cell(self):
        with open(p('out', 'sweep.csv'), encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        cells = {r['cell'] for r in rows}
        for c in ('a', 'a2', 'a85', 'a85s', 'd', 'b', 'b-full', 'c'):
            self.assertIn(c, cells)
            self.assertEqual(sum(r['cell'] == c for r in rows), REPS, c)

    def test_killed_cells_show_limit_reached_not_peak(self):
        with open(p('out', 'sweep-table.txt'), encoding='utf-8') as f:
            t = f.read()
        for line in t.splitlines():
            self.assertLessEqual(len(line), 60, line)

    def test_disturbed_runs_were_rerun(self):
        files = glob.glob(p('evidence', 'runs', '*', 'rep*', 'result.json'))
        for f in files:
            with open(f, encoding='utf-8') as fh:
                self.assertFalse(json.load(fh)['disturbed'], f)


if __name__ == '__main__':
    unittest.main()
