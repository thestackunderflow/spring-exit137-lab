# Spring Boot exit code 137 in Docker: the container OOM kill (lab)

A Spring Boot container dies with exit code 137 and its log just stops: no error, no stack trace. This lab
reproduces that in Docker, shows which field tells a kernel OOM kill apart from `docker stop` / `docker kill`, measures
why a heap allowed the whole container limit gets killed, and proves a measured fix under the same load. It is the
lab for "#26 Spring Boot Exit Code 137 in Docker" (The Stack Underflow).

Everything runs in Docker (Spring Boot 4.1.1, Java 21, Temurin 21.0.12.1, CPU only). Nothing is installed on the host.

## Intent (written before any run)

- Container limit **768m, swap off** (`memswap_limit` = `mem_limit`) in every variant except `A-swap`.
- The app (`GET /report?mb=4`) builds short-lived "reports" and keeps the last K in a bounded cache: lots of garbage,
  a small live set, **no leak**.
- Variants (JVM flags come only from `JAVA_TOOL_OPTIONS` in Compose; the image has no memory flag):

| Variant | `JAVA_TOOL_OPTIONS` | Role |
|---|---|---|
| A | `-Xmx768m` | heap allowed the whole limit |
| A2 | `-Xms768m -Xmx768m` | the same, committed from the start (expected bug) |
| A85 / A85s | `-XX:MaxRAMPercentage=85` (A85s adds `-XX:InitialRAMPercentage=85`) | a "sensible-looking" heap |
| D | none (default 25%) | the default |
| B | `-XX:MaxRAMPercentage=P` | the fix; P measured (below) |
| B-full | B + `-XX:InitialRAMPercentage=P -XX:+AlwaysPreTouch` | worst case: heap fully resident; P is read from it |
| C | B-full + N MiB direct buffers | the heap setting doesn't cover everything |
| J / J2 | `-Xmx128m` (+ `-XX:+ExitOnOutOfMemoryError`) | the JVM's own OutOfMemoryError (a log line) |
| A-swap | the bug flags, `memswap_limit` unset | the swap trap |
| S-stop / S-kill | B, then `docker stop` / `docker kill` | the other two senders of SIGKILL |

- **P rule:** non-heap as the kernel counts it = cgroup `memory.peak` - heap committed, from B-full; P = the largest
  multiple of 5 with P% x 768 + max non-heap + 10% x 768 <= 768. B-full must then survive 5/5 with `memory.peak`
  <= 90% of 768 MiB.
- Every cell runs 5 times with the same load (`load.env`); the bug cell must be killed 5/5 and the fix must survive
  5/5, or the result is reported as it is.

## Layout

- `src/` the app; `docker/Dockerfile`; `compose.bug.yaml` / `compose.fix.yaml` (the two files the video shows),
  `compose.sweep.yaml` (every other cell, flags from the environment), `compose.load.yaml` (oha).
- `scripts/` the runs (`env.sh` T0, `build.sh`, `basics.sh` T1/T2/T4, `calibrate.sh` T3, `nmt.sh` T5, `sweep.sh`,
  `captures.sh` R-oom / S-stop / S-kill / J / J2 / A-swap / R-proof, `dmesg.sh` T10).
- `tests/` T0-T14 (`test_lab.py`, `test_video_panels.py`), written before the runs; JUnit for the app.
- `evidence/` raw logs, `docker inspect`, `docker events`, `docker ps -a`, compose output per run (the account name is
  redacted to `[user]`); `out/` derived tables (`sweep.csv`, `who-killed.csv`, `fix.json`, `env.json`).
- `video/` the panel text the video uses; `video/panel-sources.json` maps each panel to its evidence file.

Run: `bash tests/run-tests.sh`.

## Results

See `LAB-STATUS.md` (measured vs expected) and `ACCURACY.md` (every number, its file and line).

## Licence

Apache License 2.0 (`LICENSE`).
