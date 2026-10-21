package lab;

import java.util.LinkedHashMap;
import java.util.Map;

/** Builds short-lived "reports" (mb MiB of byte[], every page touched) and keeps only the last K: no leak. */
public class Reports {
    private static final int MIB = 1024 * 1024;
    private static final int PAGE = 4096;
    private final Map<Long, byte[]> cache;
    private long next;

    public Reports(int keep) {
        this.cache = new LinkedHashMap<>(16, 0.75f, false) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<Long, byte[]> eldest) {
                return size() > keep;
            }
        };
    }

    public long build(int mb) {
        if (mb <= 0) return 0L;
        byte[] report = new byte[mb * MIB];
        long sum = 0;
        for (int i = 0; i < report.length; i += PAGE) {
            report[i] = (byte) ((i / PAGE) & 0x7F);
            sum += report[i];
        }
        synchronized (cache) {
            cache.put(next++, report);
        }
        return sum;
    }

    public static long expectedChecksum(int mb) {
        long sum = 0;
        for (int i = 0; i < mb * MIB; i += PAGE) sum += (i / PAGE) & 0x7F;
        return sum;
    }

    public int cached() {
        synchronized (cache) {
            return cache.size();
        }
    }

    public long cachedBytes() {
        synchronized (cache) {
            return cache.values().stream().mapToLong(b -> b.length).sum();
        }
    }
}
