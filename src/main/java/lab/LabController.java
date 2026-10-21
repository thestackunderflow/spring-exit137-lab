package lab;

import java.nio.file.Path;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LabController {
    private final Reports reports;
    private final Hold hold = new Hold();
    private final DirectHold direct = new DirectHold();

    public LabController(@Value("${lab.keep}") int keep, @Value("${lab.probe:false}") boolean probe) {
        this.reports = new Reports(keep);
        if (probe) Probe.start();
    }

    /** The app's one real endpoint: build a report, keep the last K, return its checksum. */
    @GetMapping("/report")
    public String report(@RequestParam(defaultValue = "4") int mb) {
        return Long.toString(reports.build(mb));
    }

    // ---- lab-only endpoints (never the fix, never shown as code) ----

    @GetMapping("/lab/mem")
    public Map<String, Object> mem() {
        return MemInfo.read(Path.of("/sys/fs/cgroup"));
    }

    @GetMapping("/lab/direct")
    public String direct(@RequestParam int mb) {
        direct.allocate(mb);
        return Long.toString(direct.retainedBytes());
    }

    @GetMapping("/lab/hold")
    public String hold(@RequestParam int mb) {
        return Integer.toString(hold.hold(mb, () -> { }));
    }

    @GetMapping("/lab/slow")
    public String slow(@RequestParam int seconds) throws InterruptedException {
        Thread.sleep(seconds * 1000L);
        return "done after " + seconds + " s";
    }
}
