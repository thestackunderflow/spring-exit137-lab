package lab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;

/** The app's behaviour the lab relies on (README "Intent"): short-lived reports, a bounded live set, no leak. */
class ReportsTest {

    @Test
    void cacheKeepsOnlyTheLastKReports() {
        var reports = new Reports(3);
        for (int i = 0; i < 10; i++) reports.build(1);
        assertEquals(3, reports.cached());
        assertEquals(3L * 1024 * 1024, reports.cachedBytes());
    }

    @Test
    void reportTouchesEveryPageAndReturnsAChecksum() {
        var reports = new Reports(2);
        long sum = reports.build(1);
        assertEquals(Reports.expectedChecksum(1), sum);
    }

    @Test
    void zeroMbIsAnEmptyReport() {
        assertEquals(0L, new Reports(2).build(0));
    }

    @Test
    void holdReleasesItsMemoryWhenTheHeapRunsOut() {
        // J: per-request hold; the list is local, so an OutOfMemoryError leaves nothing retained (acc S8)
        var hold = new Hold();
        assertThrows(OutOfMemoryError.class, () -> hold.hold(1, () -> { throw new OutOfMemoryError("Java heap space"); }));
        assertEquals(0, hold.retainedChunks());
    }

    @Test
    void directBuffersAreRetainedAndCounted() {
        var direct = new DirectHold();
        direct.allocate(2);
        assertEquals(2L * 1024 * 1024, direct.retainedBytes());
    }

    @Test
    void memReportsHeapAndCgroupKeys() {
        Map<String, Object> m = MemInfo.read(java.nio.file.Path.of("src/test/resources/cgroup"));
        for (String k : new String[] {"maxMemory", "totalMemory", "freeMemory", "memory.current", "memory.max",
                "memory.peak", "memory.swap.max", "memory.events"}) {
            assertTrue(m.containsKey(k), k);
        }
        assertEquals("805306368", m.get("memory.max"));
        assertEquals("1", ((Map<?, ?>) m.get("memory.events")).get("oom"));
    }

    @Test
    void probeLineFitsSixtyCells() {
        String line = Probe.line(612L * 1024 * 1024, 540L * 1024 * 1024, 401L * 1024 * 1024);
        assertEquals("LAB: cgroup 612 MiB · heap used 540 MiB · old 401 MiB", line);
        assertTrue(line.length() <= 60);
    }
}
