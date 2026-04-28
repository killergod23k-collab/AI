import os, json, time, math, random, threading, platform
import tkinter as tk
from collections import deque
from PIL import Image, ImageTk, ImageDraw
import sys
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR   = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

SYSTEM_NAME = "J.A.R.V.I.S"
MODEL_BADGE = "MARK XXXVII"

C_BG      = "#000000"
C_PRI     = "#00d4ff"
C_MID     = "#007a99"
C_DIM     = "#003344"
C_DIMMER  = "#001520"
C_ACC     = "#ff6600"
C_ACC2    = "#ffcc00"
C_TEXT    = "#8ffcff"
C_PANEL   = "#010c10"
C_GREEN   = "#00ff88"
C_RED     = "#ff3333"
C_MUTED   = "#ff3366"
C_SIDEBAR = "#020e14"


class JarvisUI:
    def __init__(self, face_path, size=None):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S — MARK XXXVII")
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        W  = min(sw, 1280)
        H  = min(sh, 820)
        self.root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.root.configure(bg=C_BG)

        self.W = W
        self.H = H

        SIDEBAR_W    = 210
        self.SB_W    = SIDEBAR_W
        self.HDR_H   = 52
        self.FTR_H   = 30
        self.CENTER_X = (W - SIDEBAR_W * 2) // 2 + SIDEBAR_W

        available_h   = H - self.HDR_H - self.FTR_H
        self.FACE_SZ  = min(int(available_h * 0.58), 380)
        self.FCX      = self.CENTER_X
        self.FCY      = self.HDR_H + int(available_h * 0.44)

        self.speaking      = False
        self.muted         = False
        self.scale         = 1.0
        self.target_scale  = 1.0
        self.halo_a        = 60.0
        self.target_halo   = 60.0
        self.last_t        = time.time()
        self.tick          = 0
        self.scan_angle    = 0.0
        self.scan2_angle   = 180.0
        self.rings_spin    = [0.0, 120.0, 240.0]
        self.pulse_r       = [0.0, self.FACE_SZ * 0.26, self.FACE_SZ * 0.52]
        self.status_text   = "INITIALISING"
        self.status_blink  = True

        self._jarvis_state = "INITIALISING"

        self.typing_queue = deque()
        self.is_typing    = False

        self.on_text_command = None

        self._face_pil         = None
        self._has_face         = False
        self._face_scale_cache = None
        self._load_face(face_path)

        # Simulated sidebar metrics
        self._cpu    = 12.0
        self._mem    = 34.0
        self._net_up = 0.4
        self._net_dn = 1.2
        self._temp   = 41.0
        self._uptime = 0
        self._sys_start = time.time()

        self._spark_cpu  = [random.uniform(5, 30) for _ in range(28)]
        self._spark_mem  = [random.uniform(28, 42) for _ in range(28)]
        self._spark_net  = [random.uniform(0.1, 2.0) for _ in range(28)]

        self.bg = tk.Canvas(self.root, width=W, height=H,
                            bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=0)

        # Log panel dimensions
        LOG_X  = self.SB_W + 10
        LOG_W  = W - self.SB_W * 2 - 20
        LOG_H  = 100
        LOG_Y  = H - self.FTR_H - LOG_H - 36

        self.log_frame = tk.Frame(self.root, bg=C_PANEL,
                                  highlightbackground=C_MID,
                                  highlightthickness=1)
        self.log_frame.place(x=LOG_X, y=LOG_Y, width=LOG_W, height=LOG_H)
        self.log_text = tk.Text(self.log_frame, fg=C_TEXT, bg=C_PANEL,
                                insertbackground=C_TEXT, borderwidth=0,
                                wrap="word", font=("Courier", 9), padx=8, pady=5)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self.log_text.tag_config("you", foreground="#e0e0e0")
        self.log_text.tag_config("ai",  foreground=C_PRI)
        self.log_text.tag_config("sys", foreground=C_ACC2)
        self.log_text.tag_config("err", foreground=C_RED)

        INPUT_Y = LOG_Y + LOG_H + 4
        self._build_input_bar(LOG_W, LOG_X, INPUT_Y)
        self._build_mute_button()

        self.root.bind("<F4>", lambda e: self._toggle_mute())

        self._api_key_ready = self._api_keys_exist()
        if not self._api_key_ready:
            self._show_setup_ui()

        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    # ── Mute button ──────────────────────────────────────────────────────────
    def _build_mute_button(self):
        BTN_W, BTN_H = 130, 30
        BTN_X = 14
        BTN_Y = self.H - self.FTR_H - BTN_H - 6

        self._mute_canvas = tk.Canvas(
            self.root, width=BTN_W, height=BTN_H,
            bg=C_BG, highlightthickness=0, cursor="hand2"
        )
        self._mute_canvas.place(x=BTN_X, y=BTN_Y)
        self._mute_canvas.bind("<Button-1>", lambda e: self._toggle_mute())
        self._draw_mute_button()

    def _draw_mute_button(self):
        c = self._mute_canvas
        c.delete("all")
        if self.muted:
            border, fill, icon, label, fg = C_MUTED, "#120005", "⊘", " MUTED", C_MUTED
        else:
            border, fill, icon, label, fg = C_GREEN, "#001208", "●", " LIVE", C_GREEN

        c.create_rectangle(0, 0, 130, 30, outline=border, fill=fill, width=1)
        c.create_text(65, 15, text=f"{icon}{label}",
                      fill=fg, font=("Courier", 10, "bold"))

    def _toggle_mute(self):
        self.muted = not self.muted
        self._draw_mute_button()
        if self.muted:
            self.set_state("MUTED")
            self.write_log("SYS: Microphone muted.")
        else:
            self.set_state("LISTENING")
            self.write_log("SYS: Microphone active.")

    # ── Input bar ────────────────────────────────────────────────────────────
    def _build_input_bar(self, lw: int, lx: int, y: int):
        BTN_W = 72
        INP_W = lw - BTN_W - 4

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            self.root,
            textvariable=self._input_var,
            fg=C_TEXT, bg="#000d12",
            insertbackground=C_TEXT,
            borderwidth=0,
            font=("Courier", 10),
            highlightthickness=1,
            highlightbackground=C_DIM,
            highlightcolor=C_PRI,
        )
        self._input_entry.place(x=lx, y=y, width=INP_W, height=28)
        self._input_entry.bind("<Return>", self._on_input_submit)
        self._input_entry.bind("<KP_Enter>", self._on_input_submit)

        self._send_btn = tk.Button(
            self.root,
            text="SEND ▸",
            command=self._on_input_submit,
            fg=C_PRI, bg=C_PANEL,
            activeforeground=C_BG, activebackground=C_PRI,
            font=("Courier", 9, "bold"),
            borderwidth=0, cursor="hand2",
            highlightthickness=1,
            highlightbackground=C_MID,
        )
        self._send_btn.place(x=lx + INP_W + 4, y=y, width=BTN_W, height=28)

    def _on_input_submit(self, event=None):
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        self.write_log(f"You: {text}")
        if self.on_text_command:
            threading.Thread(
                target=self.on_text_command,
                args=(text,),
                daemon=True
            ).start()

    # ── State ────────────────────────────────────────────────────────────────
    def set_state(self, state: str):
        self._jarvis_state = state
        if state == "MUTED":
            self.status_text = "MUTED"
            self.speaking    = False
        elif state == "SPEAKING":
            self.status_text = "SPEAKING"
            self.speaking    = True
        elif state == "THINKING":
            self.status_text = "THINKING"
            self.speaking    = False
        elif state == "LISTENING":
            self.status_text = "LISTENING"
            self.speaking    = False
        elif state == "PROCESSING":
            self.status_text = "PROCESSING"
            self.speaking    = False
        else:
            self.status_text = "ONLINE"
            self.speaking    = False

    # ── Face loader ──────────────────────────────────────────────────────────
    def _load_face(self, path):
        FW = self.FACE_SZ
        try:
            img  = Image.open(path).convert("RGBA").resize((FW, FW), Image.LANCZOS)
            mask = Image.new("L", (FW, FW), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, FW - 2, FW - 2), fill=255)
            img.putalpha(mask)
            self._face_pil = img
            self._has_face = True
        except Exception:
            self._has_face = False

    @staticmethod
    def _ac(r, g, b, a):
        f = a / 255.0
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    # ── Animation loop ───────────────────────────────────────────────────────
    def _animate(self):
        self.tick += 1
        t   = self.tick
        now = time.time()

        # Update simulated metrics
        if t % 8 == 0:
            self._cpu  = max(2, min(98, self._cpu  + random.uniform(-4, 4)))
            self._mem  = max(20, min(85, self._mem  + random.uniform(-1, 1)))
            self._temp = max(35, min(85, self._temp + random.uniform(-0.5, 0.5)))
            self._net_up = max(0.01, self._net_up + random.uniform(-0.1, 0.1))
            self._net_dn = max(0.01, self._net_dn + random.uniform(-0.2, 0.2))

        if t % 8 == 0:
            self._spark_cpu.append(self._cpu);  self._spark_cpu.pop(0)
            self._spark_mem.append(self._mem);  self._spark_mem.pop(0)
            self._spark_net.append(self._net_dn * 10); self._spark_net.pop(0)

        if now - self.last_t > (0.14 if self.speaking else 0.55):
            if self.speaking:
                self.target_scale = random.uniform(1.05, 1.11)
                self.target_halo  = random.uniform(138, 182)
            elif self.muted:
                self.target_scale = random.uniform(0.998, 1.001)
                self.target_halo  = random.uniform(20, 32)
            else:
                self.target_scale = random.uniform(1.001, 1.007)
                self.target_halo  = random.uniform(50, 68)
            self.last_t = now

        sp = 0.35 if self.speaking else 0.16
        self.scale  += (self.target_scale - self.scale)  * sp
        self.halo_a += (self.target_halo  - self.halo_a) * sp

        speeds = [1.2, -0.8, 1.9] if self.speaking else [0.5, -0.3, 0.82]
        for i, spd in enumerate(speeds):
            self.rings_spin[i] = (self.rings_spin[i] + spd) % 360

        self.scan_angle  = (self.scan_angle  + (2.8 if self.speaking else 1.2)) % 360
        self.scan2_angle = (self.scan2_angle + (-1.7 if self.speaking else -0.68)) % 360

        pspd  = 3.8 if self.speaking else 1.8
        limit = self.FACE_SZ * 0.72
        new_p = [r + pspd for r in self.pulse_r if r + pspd < limit]
        if len(new_p) < 3 and random.random() < (0.06 if self.speaking else 0.022):
            new_p.append(0.0)
        self.pulse_r = new_p

        if t % 38 == 0:
            self.status_blink = not self.status_blink

        self._draw()
        self.root.after(16, self._animate)

    # ── Main draw ─────────────────────────────────────────────────────────────
    def _draw(self):
        c    = self.bg
        W, H = self.W, self.H
        t    = self.tick
        FCX  = self.FCX
        FCY  = self.FCY
        FW   = self.FACE_SZ
        SBW  = self.SB_W
        HDR  = self.HDR_H
        FTR  = self.FTR_H
        c.delete("all")

        # ── Background fill
        c.create_rectangle(0, 0, W, H, fill=C_BG, outline="")

        # Background grid dots
        for x in range(0, W, 40):
            for y in range(HDR, H - FTR, 40):
                c.create_rectangle(x, y, x+1, y+1, fill=C_DIMMER, outline="")

        # ── Header bar ───────────────────────────────────────────────────────
        c.create_rectangle(0, 0, W, HDR, fill="#00080d", outline="")
        c.create_line(0, HDR, W, HDR, fill=C_MID, width=1)

        # Decorative header side lines
        c.create_line(0, HDR - 3, W, HDR - 3, fill=C_DIMMER, width=1)

        # Left badge
        c.create_text(SBW + 14, HDR // 2 - 6, text=MODEL_BADGE,
                      fill=C_DIM, font=("Courier", 8, "bold"), anchor="w")
        c.create_text(SBW + 14, HDR // 2 + 7, text="AUTONOMOUS MODE",
                      fill="#002233", font=("Courier", 7), anchor="w")

        # Center title
        c.create_text(W // 2, HDR // 2 - 7, text=SYSTEM_NAME,
                      fill=C_PRI, font=("Courier", 17, "bold"))
        c.create_text(W // 2, HDR // 2 + 9, text="Just A Rather Very Intelligent System",
                      fill=C_MID, font=("Courier", 8))

        # Right clock
        c.create_text(W - SBW - 14, HDR // 2 - 6,
                      text=time.strftime("%H:%M:%S"),
                      fill=C_PRI, font=("Courier", 15, "bold"), anchor="e")
        c.create_text(W - SBW - 14, HDR // 2 + 7,
                      text=time.strftime("%a  %d %b %Y"),
                      fill=C_MID, font=("Courier", 7), anchor="e")

        # ── Sidebar separators
        c.create_line(SBW, HDR, SBW, H - FTR, fill=C_DIM, width=1)
        c.create_line(W - SBW, HDR, W - SBW, H - FTR, fill=C_DIM, width=1)

        # ── Left sidebar ─────────────────────────────────────────────────────
        self._draw_left_sidebar(c, SBW, HDR, H, FTR, t)

        # ── Right sidebar ────────────────────────────────────────────────────
        self._draw_right_sidebar(c, W, SBW, HDR, H, FTR, t)

        # ── Center HUD / face ────────────────────────────────────────────────
        self._draw_center_hud(c, FCX, FCY, FW, t)

        # ── Status label + waveform ──────────────────────────────────────────
        self._draw_status_wave(c, FCX, FCY, FW, W, H, FTR, t)

        # ── Footer bar ───────────────────────────────────────────────────────
        c.create_rectangle(0, H - FTR, W, H, fill="#00080d", outline="")
        c.create_line(0, H - FTR, W, H - FTR, fill=C_DIM, width=1)
        c.create_text(W // 2, H - FTR // 2,
                      fill=C_DIM, font=("Courier", 7),
                      text="FatihMakes Industries  ·  CLASSIFIED  ·  MARK XXXVII  ·  ALL SYSTEMS NOMINAL")
        c.create_text(W - 14, H - FTR // 2, fill=C_DIM, font=("Courier", 7),
                      text="[F4] MUTE", anchor="e")

    # ── Left sidebar ─────────────────────────────────────────────────────────
    def _draw_left_sidebar(self, c, SBW, HDR, H, FTR, t):
        pad = 12
        x0  = pad
        y   = HDR + 16
        w   = SBW - pad * 2

        def section_header(label, yy):
            c.create_text(x0, yy, text=f"▸ {label}",
                          fill=C_MID, font=("Courier", 7, "bold"), anchor="w")
            c.create_line(x0, yy + 11, x0 + w, yy + 11, fill=C_DIM, width=1)
            return yy + 18

        def stat_bar(label, val, max_val, col, yy, unit=""):
            frac = max(0.0, min(1.0, val / max_val))
            c.create_text(x0, yy, text=label, fill=C_DIM,
                          font=("Courier", 7), anchor="w")
            val_str = f"{val:.0f}{unit}"
            c.create_text(x0 + w, yy, text=val_str,
                          fill=col, font=("Courier", 7, "bold"), anchor="e")
            yy += 10
            bh = 5
            c.create_rectangle(x0, yy, x0 + w, yy + bh,
                                fill=C_DIMMER, outline=C_DIM, width=1)
            bw = int(w * frac)
            if bw > 0:
                c.create_rectangle(x0, yy, x0 + bw, yy + bh, fill=col, outline="")
            return yy + bh + 7

        def sparkline(data, col, yy, height=22):
            if not data:
                return yy + height + 4
            mn, mx = min(data), max(data)
            rng = mx - mn or 1
            pts = []
            sw = w / max(len(data) - 1, 1)
            for i, v in enumerate(data):
                px = x0 + i * sw
                py = yy + height - (v - mn) / rng * height
                pts.extend([px, py])
            if len(pts) >= 4:
                c.create_line(*pts, fill=col, width=1, smooth=True)
            return yy + height + 4

        # SYSTEM PERFORMANCE
        y = section_header("SYSTEM PERFORMANCE", y)
        y = stat_bar("CPU", self._cpu, 100, C_PRI, y, "%")
        y = sparkline(self._spark_cpu, C_PRI, y)
        y = stat_bar("MEMORY", self._mem, 100, C_ACC2, y, "%")
        y = sparkline(self._spark_mem, C_ACC2, y)
        y = stat_bar("TEMP", self._temp, 100, C_ACC, y, "°C")
        y += 6

        # NETWORK
        y = section_header("NETWORK", y)
        y = stat_bar("UP", self._net_up, 10, C_GREEN, y, " MB/s")
        y = stat_bar("DOWN", self._net_dn, 10, C_PRI, y, " MB/s")
        y = sparkline(self._spark_net, C_MID, y)
        y += 6

        # UPTIME
        y = section_header("SESSION", y)
        elapsed = int(time.time() - self._sys_start)
        hh, rem = divmod(elapsed, 3600)
        mm, ss  = divmod(rem, 60)
        uptime_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        c.create_text(x0, y, text="UPTIME", fill=C_DIM, font=("Courier", 7), anchor="w")
        c.create_text(x0 + w, y, text=uptime_str, fill=C_PRI, font=("Courier", 7, "bold"), anchor="e")
        y += 14

        state_col = {
            "LISTENING": C_GREEN, "SPEAKING": C_ACC,
            "THINKING": C_ACC2, "MUTED": C_MUTED,
            "PROCESSING": C_ACC2,
        }.get(self._jarvis_state, C_PRI)
        c.create_text(x0, y, text="STATUS", fill=C_DIM, font=("Courier", 7), anchor="w")
        c.create_text(x0 + w, y, text=self._jarvis_state,
                      fill=state_col, font=("Courier", 7, "bold"), anchor="e")
        y += 18

        # TOOL PANEL
        y = section_header("ACTIVE TOOLS", y)
        tools = ["BROWSER", "FILE MGR", "WEB SEARCH", "COMPUTER", "VISION"]
        for i, tool in enumerate(tools):
            active = (t // 90 + i) % len(tools) == i % 3
            dot_col = C_GREEN if active else C_DIMMER
            c.create_rectangle(x0, y + 2, x0 + 6, y + 8, fill=dot_col, outline="")
            c.create_text(x0 + 10, y, text=tool,
                          fill=C_TEXT if active else C_DIM,
                          font=("Courier", 7), anchor="w")
            y += 14

    # ── Right sidebar ─────────────────────────────────────────────────────────
    def _draw_right_sidebar(self, c, W, SBW, HDR, H, FTR, t):
        pad = 12
        x0  = W - SBW + pad
        y   = HDR + 16
        w   = SBW - pad * 2

        def section_header(label, yy):
            c.create_text(x0, yy, text=f"▸ {label}",
                          fill=C_MID, font=("Courier", 7, "bold"), anchor="w")
            c.create_line(x0, yy + 11, x0 + w, yy + 11, fill=C_DIM, width=1)
            return yy + 18

        # SECURITY STATUS
        y = section_header("SECURITY", y)
        checks = [
            ("FIREWALL",   True),
            ("ENCRYPTION", True),
            ("INTRUSION",  True),
            ("VPN TUNNEL", False),
        ]
        for label, ok in checks:
            col = C_GREEN if ok else C_MUTED
            sym = "■" if ok else "□"
            c.create_text(x0, y, text=f"{sym} {label}", fill=col,
                          font=("Courier", 7), anchor="w")
            c.create_text(x0 + w, y, text="OK" if ok else "OFF",
                          fill=col, font=("Courier", 7, "bold"), anchor="e")
            y += 13
        y += 6

        # VOICE / AUDIO
        y = section_header("AUDIO ENGINE", y)
        voice_params = [
            ("VOICE",   "CHARON"),
            ("RATE",    "24kHz"),
            ("MODEL",   "FLASH-2.5"),
            ("LATENCY", "~220ms"),
        ]
        for label, val in voice_params:
            c.create_text(x0, y, text=label, fill=C_DIM, font=("Courier", 7), anchor="w")
            c.create_text(x0 + w, y, text=val, fill=C_TEXT, font=("Courier", 7), anchor="e")
            y += 13
        y += 6

        # CONNECTIONS
        y = section_header("CONNECTIONS", y)
        conns = [
            ("GEMINI API", True),
            ("MICROPHONE", not self.muted),
            ("SPEAKERS",   True),
            ("DISPLAY",    True),
        ]
        for label, ok in conns:
            col = C_GREEN if ok else C_MUTED
            blink_on = ok and self.status_blink
            sym = "◉" if blink_on else ("○" if ok else "✕")
            c.create_text(x0, y, text=f"{sym} {label}", fill=col,
                          font=("Courier", 7), anchor="w")
            y += 13
        y += 6

        # MEMORY
        y = section_header("MEMORY BANKS", y)
        mem_used = 68.0
        mem_pct  = mem_used / 100
        c.create_text(x0, y, text="USED", fill=C_DIM, font=("Courier", 7), anchor="w")
        c.create_text(x0 + w, y, text=f"{mem_used:.0f}%",
                      fill=C_ACC2, font=("Courier", 7, "bold"), anchor="e")
        y += 10
        c.create_rectangle(x0, y, x0 + w, y + 5, fill=C_DIMMER, outline=C_DIM, width=1)
        bw = int(w * mem_pct)
        if bw > 0:
            c.create_rectangle(x0, y, x0 + bw, y + 5, fill=C_ACC2, outline="")
        y += 14

        records = int(time.time() - self._sys_start) // 3 + 42
        c.create_text(x0, y, text="RECORDS", fill=C_DIM, font=("Courier", 7), anchor="w")
        c.create_text(x0 + w, y, text=str(records),
                      fill=C_PRI, font=("Courier", 7, "bold"), anchor="e")
        y += 18

        # LOG LEVEL
        y = section_header("ACTIVITY LOG", y)
        log_items = [
            (f"T-{int(time.time() - self._sys_start):04d}s", "BOOT OK"),
            ("LIVE", "AUDIO RX"),
            ("NOW",  self._jarvis_state),
        ]
        for ts, msg in log_items:
            c.create_text(x0, y, text=ts, fill=C_DIM, font=("Courier", 6), anchor="w")
            c.create_text(x0 + 36, y, text=msg, fill=C_TEXT, font=("Courier", 6), anchor="w")
            y += 12

        # Corner decoration bottom-right
        bx = W - SBW + 6
        by = H - FTR - 50
        bl = 16
        bc = self._ac(0, 212, 255, 80)
        c.create_line(bx, by, bx + bl, by, fill=bc, width=1)
        c.create_line(bx, by, bx, by + bl, fill=bc, width=1)
        bx2 = W - 8
        c.create_line(bx2, by, bx2 - bl, by, fill=bc, width=1)
        c.create_line(bx2, by, bx2, by + bl, fill=bc, width=1)

    # ── Center HUD ────────────────────────────────────────────────────────────
    def _draw_center_hud(self, c, FCX, FCY, FW, t):
        # Outer glow rings
        for r in range(int(FW * 0.54), int(FW * 0.28), -20):
            frac = 1.0 - (r - FW * 0.28) / (FW * 0.26)
            ga   = max(0, min(255, int(self.halo_a * 0.08 * frac)))
            if self.muted:
                gh = f"{ga:02x}"
                c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r,
                              outline=f"#{gh}0011", width=2)
            else:
                gh = f"{ga:02x}"
                c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r,
                              outline=f"#00{gh}ff", width=2)

        # Pulse rings
        for pr in self.pulse_r:
            pa = max(0, int(220 * (1.0 - pr / (FW * 0.72))))
            r  = int(pr)
            if self.muted:
                c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r,
                              outline=self._ac(255, 30, 80, pa // 3), width=2)
            else:
                c.create_oval(FCX-r, FCY-r, FCX+r, FCY+r,
                              outline=self._ac(0, 212, 255, pa), width=2)

        # Rotating ring arcs
        for idx, (r_frac, w_ring, arc_l, gap) in enumerate([
                (0.47, 3, 110, 75), (0.39, 2, 75, 55), (0.31, 1, 55, 38)]):
            ring_r = int(FW * r_frac)
            base_a = self.rings_spin[idx]
            a_val  = max(0, min(255, int(self.halo_a * (1.0 - idx * 0.18))))
            col    = self._ac(255, 30, 80, a_val) if self.muted else self._ac(0, 212, 255, a_val)
            for s in range(360 // (arc_l + gap)):
                start = (base_a + s * (arc_l + gap)) % 360
                c.create_arc(FCX-ring_r, FCY-ring_r, FCX+ring_r, FCY+ring_r,
                             start=start, extent=arc_l,
                             outline=col, width=w_ring, style="arc")

        # Scan arcs
        sr      = int(FW * 0.49)
        scan_a  = min(255, int(self.halo_a * 1.4))
        arc_ext = 70 if self.speaking else 42
        scan_col = self._ac(255, 30, 80, scan_a) if self.muted else self._ac(0, 212, 255, scan_a)
        c.create_arc(FCX-sr, FCY-sr, FCX+sr, FCY+sr,
                     start=self.scan_angle, extent=arc_ext,
                     outline=scan_col, width=3, style="arc")
        c.create_arc(FCX-sr, FCY-sr, FCX+sr, FCY+sr,
                     start=self.scan2_angle, extent=arc_ext,
                     outline=self._ac(255, 100, 0, scan_a // 2), width=2, style="arc")

        # Tick marks
        t_out = int(FW * 0.495)
        t_in  = int(FW * 0.472)
        a_mk  = self._ac(0, 212, 255, 140)
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inn = t_in if deg % 30 == 0 else t_in + 5
            c.create_line(FCX + t_out * math.cos(rad), FCY - t_out * math.sin(rad),
                          FCX + inn  * math.cos(rad), FCY - inn  * math.sin(rad),
                          fill=a_mk, width=1)

        # Crosshair
        ch_r = int(FW * 0.50)
        gap  = int(FW * 0.15)
        ch_a = self._ac(0, 212, 255, int(self.halo_a * 0.5))
        for x1, y1, x2, y2 in [
                (FCX - ch_r, FCY, FCX - gap, FCY), (FCX + gap, FCY, FCX + ch_r, FCY),
                (FCX, FCY - ch_r, FCX, FCY - gap), (FCX, FCY + gap, FCX, FCY + ch_r)]:
            c.create_line(x1, y1, x2, y2, fill=ch_a, width=1)

        # Corner brackets
        blen = 24
        bc   = self._ac(0, 212, 255, 200)
        hl = FCX - FW // 2; hr = FCX + FW // 2
        ht = FCY - FW // 2; hb = FCY + FW // 2
        for bx, by, sdx, sdy in [(hl, ht, 1, 1), (hr, ht, -1, 1),
                                   (hl, hb, 1, -1), (hr, hb, -1, -1)]:
            c.create_line(bx, by, bx + sdx * blen, by,            fill=bc, width=2)
            c.create_line(bx, by, bx,               by + sdy * blen, fill=bc, width=2)

        # Face image or orb
        if self._has_face:
            fw = int(FW * self.scale)
            if (self._face_scale_cache is None or
                    abs(self._face_scale_cache[0] - self.scale) > 0.004):
                scaled = self._face_pil.resize((fw, fw), Image.BILINEAR)
                tk_img = ImageTk.PhotoImage(scaled)
                self._face_scale_cache = (self.scale, tk_img)
            c.create_image(FCX, FCY, image=self._face_scale_cache[1])
        else:
            orb_r     = int(FW * 0.27 * self.scale)
            orb_color = (255, 30, 80) if self.muted else (0, 65, 120)
            for i in range(7, 0, -1):
                r2   = int(orb_r * i / 7)
                frac = i / 7
                ga   = max(0, min(255, int(self.halo_a * 1.1 * frac)))
                c.create_oval(FCX-r2, FCY-r2, FCX+r2, FCY+r2,
                              fill=self._ac(int(orb_color[0]*frac),
                                            int(orb_color[1]*frac),
                                            int(orb_color[2]*frac), ga),
                              outline="")
            c.create_text(FCX, FCY, text=SYSTEM_NAME,
                          fill=self._ac(0, 212, 255, min(255, int(self.halo_a * 2))),
                          font=("Courier", 14, "bold"))

    # ── Status + waveform ─────────────────────────────────────────────────────
    def _draw_status_wave(self, c, FCX, FCY, FW, W, H, FTR, t):
        SBW  = self.SB_W
        CW   = W - SBW * 2

        sy = FCY + FW // 2 + 22

        # State text
        if self.muted:
            stat, sc = "⊘ MUTED", C_MUTED
        elif self.speaking:
            stat, sc = "● SPEAKING", C_ACC
        elif self._jarvis_state == "THINKING":
            sym  = "◈" if self.status_blink else "◇"
            stat, sc = f"{sym} THINKING", C_ACC2
        elif self._jarvis_state == "PROCESSING":
            sym  = "▷" if self.status_blink else "▶"
            stat, sc = f"{sym} PROCESSING", C_ACC2
        elif self._jarvis_state == "LISTENING":
            sym  = "●" if self.status_blink else "○"
            stat, sc = f"{sym} LISTENING", C_GREEN
        else:
            sym  = "●" if self.status_blink else "○"
            stat, sc = f"{sym} {self.status_text}", C_PRI

        c.create_text(FCX, sy, text=stat, fill=sc,
                      font=("Courier", 11, "bold"))

        # Waveform bars
        wy = sy + 18
        N  = 44
        BH = 20
        bw = 7
        total_w = N * bw
        wx0 = FCX - total_w // 2

        for i in range(N):
            if self.muted:
                hb  = 2
                col = C_MUTED
            elif self.speaking:
                hb  = random.randint(3, BH)
                col = C_PRI if hb > BH * 0.6 else C_MID
            else:
                phase = t * 0.07 + i * 0.52
                hb    = int(3 + 2.5 * abs(math.sin(phase)))
                col   = C_DIM
            bx = wx0 + i * bw
            c.create_rectangle(bx, wy + BH - hb, bx + bw - 2, wy + BH,
                                fill=col, outline="")

        # Log panel label
        LOG_X = SBW + 10
        LOG_H = 100
        LOG_Y = H - FTR - LOG_H - 36
        c.create_text(LOG_X + 6, LOG_Y - 10, text="◈ COMMUNICATION LOG",
                      fill=C_MID, font=("Courier", 7, "bold"), anchor="w")

    # ── Log writer ───────────────────────────────────────────────────────────
    def write_log(self, text: str):
        self.typing_queue.append(text)
        tl = text.lower()
        if tl.startswith("you:"):
            self.set_state("PROCESSING")
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            self.set_state("SPEAKING")
        if not self.is_typing:
            self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing = False
            if not self.speaking and not self.muted:
                self.set_state("LISTENING")
            return
        self.is_typing = True
        text = self.typing_queue.popleft()
        tl   = text.lower()
        if tl.startswith("you:"):
            tag = "you"
        elif tl.startswith("jarvis:") or tl.startswith("ai:"):
            tag = "ai"
        elif tl.startswith("err:") or "error" in tl or "failed" in tl:
            tag = "err"
        else:
            tag = "sys"
        self.log_text.configure(state="normal")
        self._type_char(text, 0, tag)

    def _type_char(self, text, i, tag):
        if i < len(text):
            self.log_text.insert(tk.END, text[i], tag)
            self.log_text.see(tk.END)
            self.root.after(7, self._type_char, text, i + 1, tag)
        else:
            self.log_text.insert(tk.END, "\n")
            self.log_text.configure(state="disabled")
            self.root.after(20, self._start_typing)

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")

    # ── API key helpers ──────────────────────────────────────────────────────
    def _api_keys_exist(self) -> bool:
        if not API_FILE.exists():
            return False
        try:
            data = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(data.get("gemini_api_key")) and bool(data.get("os_system"))
        except Exception:
            return False

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    @staticmethod
    def _detect_os() -> str:
        s = platform.system().lower()
        if s == "darwin":
            return "mac"
        if s == "windows":
            return "windows"
        return "linux"

    # ── Setup modal ──────────────────────────────────────────────────────────
    def _show_setup_ui(self):
        detected = self._detect_os()
        self._selected_os = tk.StringVar(value=detected)

        self.setup_frame = tk.Frame(
            self.root, bg="#00080d",
            highlightbackground=C_PRI, highlightthickness=1
        )
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        tk.Label(
            self.setup_frame,
            text="◈  INITIALISATION REQUIRED",
            fg=C_PRI, bg="#00080d",
            font=("Courier", 13, "bold")
        ).pack(pady=(20, 2))
        tk.Label(
            self.setup_frame,
            text="Configure J.A.R.V.I.S. before first boot.",
            fg=C_MID, bg="#00080d",
            font=("Courier", 9)
        ).pack(pady=(0, 16))

        # Separator
        tk.Frame(self.setup_frame, bg=C_DIM, height=1).pack(fill="x", padx=20, pady=(0, 14))

        # API key
        tk.Label(
            self.setup_frame, text="GEMINI API KEY",
            fg=C_DIM, bg="#00080d", font=("Courier", 9)
        ).pack(pady=(0, 3))
        self.gemini_entry = tk.Entry(
            self.setup_frame, width=50,
            fg=C_TEXT, bg="#000d12",
            insertbackground=C_TEXT,
            borderwidth=0, font=("Courier", 10), show="*",
            highlightthickness=1, highlightbackground=C_MID, highlightcolor=C_PRI
        )
        self.gemini_entry.pack(pady=(0, 18), padx=24)

        # Separator
        tk.Frame(self.setup_frame, bg=C_DIM, height=1).pack(fill="x", padx=20, pady=(0, 12))

        # OS selector
        tk.Label(
            self.setup_frame, text="SELECT OPERATING SYSTEM",
            fg=C_DIM, bg="#00080d", font=("Courier", 9)
        ).pack(pady=(0, 4))

        detect_label = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}.get(
            detected, detected.capitalize()
        )
        tk.Label(
            self.setup_frame, text=f"AUTO-DETECTED: {detect_label}",
            fg=C_ACC2, bg="#00080d", font=("Courier", 8)
        ).pack(pady=(0, 8))

        os_btn_frame = tk.Frame(self.setup_frame, bg="#00080d")
        os_btn_frame.pack(pady=(0, 18))

        os_options = [
            ("windows", "⊞  WINDOWS"),
            ("mac",     "  macOS"),
            ("linux",   "🐧  LINUX"),
        ]
        self._os_buttons = {}
        for os_key, os_label in os_options:
            btn = tk.Button(
                os_btn_frame, text=os_label, width=13,
                font=("Courier", 10, "bold"), borderwidth=0,
                cursor="hand2", pady=7,
                command=lambda k=os_key: self._select_os(k)
            )
            btn.pack(side="left", padx=6)
            self._os_buttons[os_key] = btn

        self._select_os(detected)

        # Separator
        tk.Frame(self.setup_frame, bg=C_DIM, height=1).pack(fill="x", padx=20, pady=(0, 14))

        # Init button
        tk.Button(
            self.setup_frame,
            text="▸  INITIALISE SYSTEMS",
            command=self._save_api_keys,
            bg=C_BG, fg=C_PRI,
            activebackground="#003344",
            activeforeground=C_PRI,
            font=("Courier", 11, "bold"),
            borderwidth=0, pady=9, padx=20,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=C_MID,
        ).pack(pady=(0, 20))

    def _select_os(self, os_key: str):
        self._selected_os.set(os_key)
        styles = {
            "windows": (C_PRI,   "#001a22"),
            "mac":     (C_ACC2,  "#1a1500"),
            "linux":   (C_GREEN, "#001a0d"),
        }
        for key, btn in self._os_buttons.items():
            if key == os_key:
                fg, bg = styles[key]
                btn.configure(fg=bg, bg=fg,
                               activeforeground=bg, activebackground=fg,
                               relief="flat")
            else:
                btn.configure(fg=C_DIM, bg="#000d12",
                               activeforeground=C_TEXT, activebackground="#001a22",
                               relief="flat")

    def _save_api_keys(self):
        gemini = self.gemini_entry.get().strip()
        if not gemini:
            self.gemini_entry.configure(highlightbackground=C_RED, highlightcolor=C_RED)
            return

        os_system = self._selected_os.get()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(API_FILE, "w", encoding="utf-8") as f:
            json.dump({"gemini_api_key": gemini, "os_system": os_system}, f, indent=4)

        self.setup_frame.destroy()
        self._api_key_ready = True
        self.set_state("LISTENING")
        self.write_log(f"SYS: Systems initialised. OS → {os_system.upper()}. JARVIS online.")
