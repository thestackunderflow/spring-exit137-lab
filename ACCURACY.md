# ACCURACY: every number and string the video can show, mapped to its file and line

Captured 21 Oct 2026 (UTC 03:33-04:21) on Docker Engine 27.4.0 / Docker Desktop 4.37.1, containerd 1.7.21, WSL 2
kernel 6.18.33.2-microsoft-standard-WSL2, VM MemTotal 14310064 kB, SwapTotal 4194304 kB, 20 CPUs, i7-14700F
(`out/env.json`). Spring Boot 4.1.1, Java 21.0.12.1 (`evidence/runs/r-oom/stdout.txt` L9, L11). Vendor sources are in
the plan's `Refream-Canvas/inputs/video-plans/2026-10-20-exit-137/ACCURACY.md` (rev. 2); this file covers the lab.

Rounding: MiB = bytes / 1048576, rounded down in the sweep table, to nearest in the NMT table. "peak" = cgroup
`memory.peak` read by `/lab/mem` after the load (survivors only; killed cells show "limit reached").

## The captures (one session, `captures-20261021T0418..`, probe off)

| Claim / on-screen text | Value | File : line |
|---|---|---|
| Compose's line | `app-1 exited with code 137` | `evidence/runs/r-oom/compose-up.txt` L28 (preceded by an ANSI erase code) |
| `docker ps -a` | `exit137-app-1   Exited (137) Less than a second ago` | `evidence/runs/r-oom/ps.txt` L1 |
| `ExitCode` / `OOMKilled` | `"ExitCode": 137,` / `"OOMKilled": true,` | `evidence/runs/r-oom/inspect.json` L18 / L15 |
| The flags the run read | `Picked up JAVA_TOOL_OPTIONS: -Xms768m -Xmx768m` (first stderr line) | `evidence/runs/r-oom/stderr.txt` L1; `compose.bug.yaml` L9 |
| Last app log line | `Completed initialization in 1 ms` (DispatcherServlet, the readiness request) | `evidence/runs/r-oom/stdout.txt` L21 |
| Started in | `Started LabApplication in 1.193 seconds` | `evidence/runs/r-oom/stdout.txt` L18 |
| Requests served before the kill | 373 x 200; then 1619 `Connection refused`, 6 `connection closed before message completed`, 2 `connection error` | `evidence/runs/r-oom/oha.txt` L43, L46-48 |
| Trailing silence (last line -> FinishedAt) | **0.99 s** (FinishedAt 04:18:15.963855652Z, last line 04:18:14.974Z) | `evidence/runs/r-oom/result.json` `tail_s`; `inspect.json` L21 |
| Docker events, kernel kill | `oom`, then `die exitCode=137`; **no `kill` event** | `evidence/runs/r-oom/events.jsonl` L4, L5 |
| Kernel log (T10) | `Memory cgroup out of memory: Killed process 7606 (java)` (VM PID) | `evidence/t10/dmesg-oom.txt` L2 (matched to the container by its cgroup ID, L1) |
| docker stop | 137, `OOMKilled` false, `Commencing graceful shutdown. Waiting for active requests to complete`, events `kill signal=15`, `kill signal=9`, `die`; stop took 10.33 s; trailing silence 10.0 s | `evidence/runs/s-stop/` `stdout.txt` L22, `events.jsonl` L4, L5, L7, `result.json` |
| docker kill | 137, `OOMKilled` false, events `kill signal=9`, `die`; no shutdown line | `evidence/runs/s-kill/events.jsonl` L4-5, `result.json` |
| Proof (B, same session) | `[200] 2000 responses`, `Success rate: 100.00%`, after the load `"Running": true`, `"OOMKilled": false`; memory.peak 473710592 B = **451 MiB of 768** | `evidence/runs/r-proof/oha.txt` L43, L2; `state-after.pretty.json`; `mem-after.json` |
| Proof ending (lab only) | `Graceful shutdown complete`, exit 143 (`docker stop -t 30`) | `evidence/runs/r-proof/stdout.txt` L23; `result.json` |
| Java's own OOM (J, `-Xmx128m`) | `java.lang.OutOfMemoryError: Java heap space` in the log, HTTP 500, still running 10 s later, OOMKilled false | `evidence/runs/j/stdout.txt` L22 (ERROR), L24; `hold-status.txt`; `running-10s-after.txt` |
| J2 (`+ExitOnOutOfMemoryError`) | `Terminating due to java.lang.OutOfMemoryError: Java heap space` on stdout, exit **3**, OOMKilled false, `die exitCode=3` | `evidence/runs/j2/stdout.txt` L22; `result.json` |
| A-swap (bug flags, `memswap_limit` unset) | `memory.swap.max` 805306368; `Memory & Swap Limit: 1.50G`; **survived** the load, memory.peak = 805306368 (the RAM limit), 154972160 B (147 MiB) in swap | `evidence/runs/a-swap/mem-after.json`; `evidence/t4/a-swap-system.txt` L18 |

## What Java sees (T4, Compose-started, 768m)

| Claim | Value | File : line |
|---|---|---|
| Provider / limit | `Provider: cgroupv2`, `Memory Limit: 768.00M` | `evidence/t4/b-system.txt` L5, L16 |
| MaxHeapSize | A / A2 805306368; D 201326592 (25%); B 603979776 (75%) | `evidence/t4/{a,a2,d,b}-flags.txt` L199 |
| GC | `UseSerialGC = true` (ergonomic) in every cell | `evidence/t4/*-flags.txt` L491; `out/basics.json` |
| `Runtime.maxMemory()` for B | 583860224 (556.8 MiB) = MaxHeapSize minus one survivor space (acc M5; not shown) | `evidence/runs/r-proof/mem-after.json` |

## The sweep (5 reps each, probe on, same `load.env`: K=16, MB=4, N=2000, C=8)

| Cell | Setting | Killed | Peak of survivors (MiB, max) | File |
|---|---|---|---|---|
| A | `-Xmx768m` | 0/5 | 484 | `evidence/runs/a/rep*/result.json` |
| **A2 (bug)** | `-Xms768m -Xmx768m` | **5/5** | limit reached | `evidence/runs/a2/rep*/` (each: oom then die 137, no kill; 367-373 requests served) |
| A85 | `-XX:MaxRAMPercentage=85` | 0/5 | 470 | `evidence/runs/a85/` |
| A85s | `-XX:MaxRAMPercentage=85 -XX:InitialRAMPercentage=85` | **2/5** | 752 (the 3 survivors: 744-752) | `evidence/runs/a85s/` |
| D | no flag | 0/5 | 331 | `evidence/runs/d/` |
| B (fix) | `-XX:MaxRAMPercentage=75` | 0/5 | 455 | `evidence/runs/b/` |
| B-full | B + `-XX:InitialRAMPercentage=75 -XX:+AlwaysPreTouch` (+ NMT flags) | 0/5 | 686 (<= 691.2 = 90%) | `evidence/runs/b-full/` |
| C | B-full + 128 MiB direct buffers | **5/5** | limit reached; killed **during** `/lab/direct?mb=128`, before the load | `evidence/runs/c/`, `out/direct.json` |

Table as shown: `out/sweep-table.txt` (= `video/ch6-sweep-table.txt`). Raw rows: `out/sweep.csv`.
Trailing silence of the 6 bug-cell runs (A2 rep1-5, r-oom): 1.035, 1.041, 1.091, 2.318, 1.533, 0.99 s.

## P (T5)

| Claim | Value | File |
|---|---|---|
| non-heap as the kernel counts it (memory.peak - NMT Java Heap committed), B-full | 109.4-113.4 MiB over 8 runs (P=50 x3, P=75 x5); max **113.4** | `out/fix.json` L13, `runs` |
| P rule | 75% x 768 + 113.4 + 76.8 = 766.2 <= 768; 80% would give 804.6 | `out/fix.json` L14 |
| P | **75** | `out/fix.json` L2 |
| NMT split (B-full rep1, committed) | Java Heap 576, Metaspace 30, Code 15, everything else 38 MiB (NMT total minus those three) | `evidence/runs/b-full/rep1/nmt.txt` L7, L85, L30; `out/nmt-table.txt` |
| NMT vs kernel | NMT non-heap ~83 MiB vs kernel-counted 113 MiB: the cgroup also charges page cache, malloc slack, kernel memory (acc M2) | same |

## Who killed it (the aligned table, `video/ch3-who-killed.txt` = `out/who-killed.txt`)

`docker stop` 137 / `Commencing grace...` / `kill 15,9` / false; `docker kill` 137 / `Completed initia...` / `kill 9` /
false; kernel OOM 137 / `Completed initia...` / `oom` / true. Source rows: `out/who-killed.csv` (full last lines).

## Panels and code files the video pins

`video/panel-sources.json` maps each `video/*.txt` panel to its source files; `tests/test_video_panels.py` (T14) checks
every panel line is verbatim in a source and <= 60 cells. Code cards: `compose.bug.yaml`, `compose.fix.yaml` (same 13
rows, one changed row L9, change starts at the same column; T13). `docker/Dockerfile` (not a card in rev. 2).
