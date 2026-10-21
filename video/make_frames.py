"""Frame-0 cards (light terminal look) built from the lab's captured panel files, never retyped:
- frames/hook-landscape.png (1600x1000): the intro slide's right half (ch0-terminal.txt + hook-callout.txt)
- frames/short-frame0.png (1080x1440): the Short's frame-0 overlay (the area above the caption band, KEEP_BOTTOM 0.25)
Run (no host installs): docker run --rm -v "<lab>/video:/v" tsu-thumbs:0.1 python3 /v/make_frames.py
"""
from PIL import Image, ImageDraw, ImageFont

MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
INK, RED, MUTED, BLUE = '#1a2230', '#c62828', '#5b6678', '#1d4ed8'


def lines(name):
    with open(f'/v/{name}', encoding='utf-8') as f:
        return [ln.rstrip('\n') for ln in f if ln.strip()]


T = lines('ch0-terminal.txt')      # compose line, docker ps line, "ExitCode": 137,  "OOMKilled": true,
FLAGS = lines('hook-callout.txt')[0]  # Picked up JAVA_TOOL_OPTIONS: -Xms768m -Xmx768m
# the docker ps line is shown with its column padding squeezed to fit; the text is otherwise verbatim
ROWS = [('$ docker compose -f compose.bug.yaml up app', MUTED), (T[0], RED), ('', INK),
        ("$ docker ps -a --format '{{.Names}} {{.Status}}'", MUTED), (' '.join(T[1].split()), INK), ('', INK),
        ('$ docker inspect exit137-app-1   (State, 2 of 11 keys)', MUTED), (T[3], RED), (T[2], RED), ('', INK),
        ('first line of the app log:', MUTED), (FLAGS, BLUE)]   # inspect keys in captured order (OOMKilled L15, ExitCode L18)


def card(path, W, H, size, title, note, rows):
    im = Image.new('RGB', (W, H), '#f6f7f9')
    d = ImageDraw.Draw(im)
    m = int(W * 0.04)
    top = int(H * 0.06) if W > H else int(H * 0.10)
    d.rounded_rectangle((m, top, W - m, H - top - 60), 24, fill='#ffffff', outline='#d8dde5', width=4)
    d.rectangle((m + 2, top + 2, W - m - 2, top + 70), fill='#e3e7ee')
    for i, c in enumerate(('#e5534b', '#d9a400', '#2da44e')):
        d.ellipse((m + 30 + i * 42, top + 22, m + 56 + i * 42, top + 48), fill=c)
    d.text((m + 180, top + 18), title, font=ImageFont.truetype(BOLD, int(size * 0.8)), fill=INK)
    f = ImageFont.truetype(MONO, size)
    fb = ImageFont.truetype(BOLD, size)
    y = top + 110
    for text, col in rows:
        if col == BLUE:   # the answer row: boxed so it reads at phone size
            w = d.textlength(text, font=fb)
            d.rounded_rectangle((m + 28, y - 8, m + 52 + w, y + size + 12), 10, fill='#e8efff', outline=BLUE, width=3)
        d.text((m + 40, y), text, font=fb if col in (RED, BLUE) else f, fill=col)
        y += int(size * 1.55)
    d.text((m + 6, H - top - 40), note, font=ImageFont.truetype(MONO, int(size * 0.62)), fill=MUTED)
    im.save(path)


card('/v/frames/hook-landscape.png', 1600, 1000, 34, 'Spring Boot 4.1.1 · 768 MiB container',
     'Real lab run r-oom, 21 Oct 2026: selected output lines as captured (docker ps spacing trimmed), spring-exit137-lab', ROWS)
SHORT = [(T[0], RED), ('', INK), (T[3], RED), (T[2], RED), ('', INK), ('no error in the app log', MUTED),
         ('no stack trace', MUTED)]
card('/v/frames/short-frame0.png', 1080, 1440, 54, '768 MiB container',
     'Real lab run r-oom, 21 Oct 2026', SHORT)
