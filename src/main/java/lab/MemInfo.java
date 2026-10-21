package lab;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/** /lab/mem: the JVM's heap numbers and the container's cgroup v2 memory files, as read (strings, no rounding). */
public final class MemInfo {
    private MemInfo() {
    }

    public static Map<String, Object> read(Path cgroup) {
        Runtime rt = Runtime.getRuntime();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("maxMemory", rt.maxMemory());
        m.put("totalMemory", rt.totalMemory());
        m.put("freeMemory", rt.freeMemory());
        for (String f : new String[] {"memory.current", "memory.max", "memory.peak", "memory.swap.max", "memory.swap.current"}) {
            m.put(f, file(cgroup.resolve(f)));
        }
        Map<String, String> events = new LinkedHashMap<>();
        String ev = file(cgroup.resolve("memory.events"));
        if (ev != null) {
            for (String line : ev.split("\n")) {
                String[] kv = line.trim().split(" ");
                if (kv.length == 2) events.put(kv[0], kv[1]);
            }
        }
        m.put("memory.events", events);
        return m;
    }

    static String file(Path p) {
        try {
            return Files.readString(p).trim();
        } catch (IOException e) {
            return null;
        }
    }
}
