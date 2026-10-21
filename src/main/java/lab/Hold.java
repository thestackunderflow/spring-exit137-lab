package lab;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/** Variant J: holds mb MiB on the heap for ONE request; the list is local, so an OutOfMemoryError retains nothing. */
public class Hold {
    private static final int MIB = 1024 * 1024;
    private final AtomicInteger retained = new AtomicInteger();

    public int hold(int mb, Runnable afterEachChunk) {
        List<byte[]> chunks = new ArrayList<>();
        try {
            for (int i = 0; i < mb; i++) {
                chunks.add(new byte[MIB]);
                retained.incrementAndGet();
                afterEachChunk.run();
            }
            return chunks.size();
        } finally {
            retained.addAndGet(-chunks.size());
            chunks.clear();
        }
    }

    public int retainedChunks() {
        return retained.get();
    }
}
