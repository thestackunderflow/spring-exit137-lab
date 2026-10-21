package lab;

import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

/** Variant C: retains mb MiB of direct (off-heap) buffers. allocateDirect zeroes them, so the pages are resident. */
public class DirectHold {
    private static final int MIB = 1024 * 1024;
    private final List<ByteBuffer> buffers = new ArrayList<>();

    public synchronized void allocate(int mb) {
        for (int i = 0; i < mb; i++) buffers.add(ByteBuffer.allocateDirect(MIB));
    }

    public synchronized long retainedBytes() {
        return buffers.stream().mapToLong(ByteBuffer::capacity).sum();
    }
}
