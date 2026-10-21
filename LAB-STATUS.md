# LAB-STATUS (21 Oct 2026)

**Done.** T0-T14 written first (red: `tests/out/red-run.log`, 37 Python tests, JUnit did not compile), then green:
7/7 JUnit + 37/37 Python (`tests/out/test-run.log`). Every run is Docker-only; no rep was flagged as disturbed (other
jobs below 11% CPU summed, host free RAM >= 4 GB at every start; `evidence/runs/*/stats-*.txt`).

## Measured vs expected (PLAN rev. 2)

| Plan expectation | Measured | Consequence for the script |
|---|---|---|
| GC is Serial in 768 MiB (acc M1) | `UseSerialGC = true` in every cell | J15 confirmed |
| A (`-Xmx768m`) exp. survives | **0/5 killed**, peak <= 484 MiB | one sentence: "`-Xmx768m` alone survived this load, the heap only grows when it has to" |
| A2 (`-Xms768m -Xmx768m`) exp. killed | **5/5 killed** (oom, die 137, no kill event) after 367-373 requests | **A2 is the bug** (T3 stop rule); `compose.bug.yaml` shows A2 |
| A85 "skill issue" | `MaxRAMPercentage=85` 0/5 killed (peak 470); **`Max+InitialRAMPercentage=85` 2/5 killed**, survivors peaked at 744-752 MiB of 768 | hook option: "even 85% with Xms = Xmx got killed 2 times in 5"; Alt 1 title "Below the Limit" is supportable (a heap at 85% of the limit was killed) |
| D (default) | survives 5/5, peak 331 MiB, MaxHeapSize 192 MiB | "safe, but uses well under half of the 768" |
| P from B-full | non-heap (kernel) 109.4-113.4 MiB; **P = 75**; B-full 5/5, peak 686 MiB (<= 691.2) | "75 here because the staff measured 113 MiB" |
| B (fix) | 5/5 survive, peak <= 455 MiB; R-proof 2000/2000, peak 451 MiB | proof line |
| C kills | **5/5 killed**, but **during** the 128 MiB direct allocation, before the load | wording: "we asked for 128 megabytes of direct buffers on top of a full heap, and the marshal came before that request finished" |
| J / J2 | OOME line + HTTP 500, still running 10 s later; J2 exit 3 | as planned |
| A-swap | **survived** with 147 MiB in swap, memory.peak = 768 MiB | the swap trap is real on this host: without `memswap_limit`, the bug config survives by swapping (one sentence, ch. 4) |
| T10 kernel line | captured: `Memory cgroup out of memory: Killed process 7606 (java)` | description / pinned comment |
| E-trail silence row in the R-oom replay | **tail 0.99 s: no row** (threshold 1 s). The bug cell's tails: 0.99-2.32 s (4 of 6 runs over 1 s). The app dies ~0.7 s after the load starts | **script change**: ch. 2 has no "no output for N s" row before the exit row; the VO says the load started and the container was gone a second later, 373 requests in. The S-stop capture shows the row (`no output for 10.0 s`), but S-stop is a table row only. Not re-captured to get a row (that would be picking a run for a visual) |
| frame 0's last line | `Completed initialization in 1 ms` (acc M4) | as planned |

## Files

- Code cards: `compose.bug.yaml`, `compose.fix.yaml` (one changed row, L9). Dockerfile: `docker/Dockerfile`.
- Panels: `video/*.txt`, sources in `video/panel-sources.json`; replays: `evidence/replays/{r-oom,r-proof,s-stop}/`
  (`run.meta.json` has `finishedAt` + `tExitMs`, E-trail).
- Numbers -> files: `ACCURACY.md`. Tables: `out/sweep-table.txt`, `out/who-killed.txt`, `out/nmt-table.txt`.

## Re-run

`bash scripts/env.sh; bash scripts/build.sh; bash scripts/basics.sh a a2 d; bash scripts/calibrate.sh;
bash scripts/nmt.sh; bash scripts/basics.sh b a-swap; bash scripts/sweep.sh; SESSION=x bash scripts/captures.sh r-oom;
bash scripts/dmesg.sh; SESSION=x bash scripts/captures.sh s-stop s-kill r-proof j j2 a-swap;
py scripts/tables.py; py scripts/panels.py; bash tests/run-tests.sh`
