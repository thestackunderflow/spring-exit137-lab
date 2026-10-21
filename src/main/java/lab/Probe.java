package lab;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryPoolMXBean;
import java.nio.file.Path;

/** M-runs only (lab.probe=true): one LAB: line per second on stdout. A plain daemon thread, not a Spring bean. */
public final class Probe {
    private static final long MIB = 1024 * 1024;

    private Probe() {
    }

    public static String line(long cgroupBytes, long heapUsed, long oldUsed) {
        return "LAB: cgroup " + cgroupBytes / MIB + " MiB · heap used " + heapUsed / MIB + " MiB · old " + oldUsed / MIB + " MiB";
    }

    static void start() {
        Thread t = new Thread(() -> {
            var heap = ManagementFactory.getMemoryMXBean();
            MemoryPoolMXBean old = ManagementFactory.getMemoryPoolMXBeans().stream()
                    .filter(p -> p.getName().contains("Old") || p.getName().contains("Tenured")).findFirst().orElse(null);
            Path current = Path.of("/sys/fs/cgroup/memory.current");
            while (true) {
                try {
                    String c = MemInfo.file(current);
                    long cg = c == null ? 0 : Long.parseLong(c);
                    System.out.println(line(cg, heap.getHeapMemoryUsage().getUsed(), old == null ? 0 : old.getUsage().getUsed()));
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    return;
                } catch (RuntimeException e) {
                    // keep probing
                }
            }
        }, "lab-probe");
        t.setDaemon(true);
        t.start();
    }
}
