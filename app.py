import tkinter as tk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

from models import SEIR
from plot import plot_heatmap

# nazwa argumentu SEIR: (domyślna, min, max, krok)
PARAMS = dict(
    S=(9990, 0, 100000, 10),
    I=(10, 0, 5000, 1),
    R=(0, 0, 100000, 10),
    E=(0, 0, 5000, 1),
    infectionFactor=(0.5, 0, 3, 0.01),
    infectionPeroid=(7, 1, 30, 0.5),
    incubationPeroid=(5, 1, 30, 0.5),
    immunityPeroid=(180, 1, 1000, 1),
    lethality=(0.1, 0, 1, 0.01),
    naturalLethality=(1 / (70 * 365), 0, 1e-3, 1e-6),
)

LABELS = dict(
    S="Podatni (S)",
    I="Zakażeni (I)",
    R="Ozdrowieni / odporni (R)",
    E="Zarażeni, nie zarażający innych (E)",
    infectionFactor="Współczynnik infekcji (β)",
    infectionPeroid="Okres zakaźności [dni] (γ)",
    incubationPeroid="Okres inkubacji [dni] (σ)",
    immunityPeroid="Czas odporności [dni] (ω)",
    lethality="Śmiertelność choroby (α)",
    naturalLethality="Śmiertelność naturalna [1/dzień] (μ)",
)

INT_PARAMS = {"S", "I", "R", "E"}
BG = "#242424"
PANEL = "#2b2b2b"
FG = "#e0e0e0"
ACCENT = "#5ab0ff"


def fmt(name, v):
    if name in INT_PARAMS:
        return f"{int(round(v))}"
    if PARAMS[name][2] < 0.01:
        return f"{v:.2e}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def clean(name, v):
    step = PARAMS[name][3]
    if name in INT_PARAMS:
        return int(round(v))
    return round(v / step) * step


class Window(tk.Tk):
    def __init__(self, dt=0.1, steps_per_frame=5, interval=30):
        super().__init__()
        self.dt, self.spf, self.interval = dt, steps_per_frame, interval
        self.model = None
        self.running = False
        self._job = None
        self._resize_job = None
        self._busy = False
        self._busy_job = None
        self.configure(bg=BG)
        self.title("SEIRS epidemic simulation")
        self.geometry("1150x720")
        self.init_window()

    def init_window(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = tk.Frame(self, bg=PANEL, width=320)
        panel.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)
        panel.grid_propagate(False)

        tk.Label(panel, text="Parametry modelu", bg=PANEL, fg=FG,
                 font=("TkDefaultFont", 11, "bold")).pack(pady=(10, 4))

        self.entries = {}
        self.value_labels = {}
        for name, (val, lo, hi, step) in PARAMS.items():
            row = tk.Frame(panel, bg=PANEL)
            row.pack(fill="x", padx=10, pady=(6, 0))
            tk.Label(row, text=LABELS[name], bg=PANEL, fg=FG,
                     anchor="w").pack(side="left")
            vl = tk.Label(row, text=fmt(name, val), bg=PANEL, fg=ACCENT,
                          anchor="e")
            vl.pack(side="right")

            s = tk.Scale(panel, from_=lo, to=hi, resolution=step,
                         orient="horizontal", showvalue=False,
                         bg=PANEL, fg=FG, troughcolor=BG,
                         highlightthickness=0, bd=0, sliderrelief="flat",
                         activebackground=ACCENT)
            s.set(val)
            s.pack(fill="x", padx=10, pady=(0, 2))
            self.entries[name] = s
            self.value_labels[name] = vl

        btns = tk.Frame(panel, bg=PANEL)
        btns.pack(fill="x", padx=10, pady=(14, 4))
        self.buttonRun = tk.Button(btns, text="Start", command=self.toggle,
                                   bg="#1f6aa5", fg="white", relief="flat",
                                   activebackground="#2a80c5", bd=0, pady=6)
        self.buttonRun.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.buttonReset = tk.Button(btns, text="Reset", command=self.reset,
                                     bg=PANEL, fg=FG, relief="solid", bd=1,
                                     activebackground="#3a3a3a", pady=6)
        self.buttonReset.pack(side="left", expand=True, fill="x", padx=(4, 0))

        plot_frame = tk.Frame(self, bg=BG)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        self.fig = Figure(figsize=(8, 7), facecolor=BG, layout="constrained")
        self.axes = self.fig.subplots(2, 2)
        self.images = {}

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=BG, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=6, pady=6)

        # debounce resize zamiast przerysowania przy każdym Configure
        widget.unbind("<Configure>")
        widget.bind("<Configure>", self.on_canvas_configure)
        self.bind("<Configure>", self.on_window_configure)

        self.ani = animation.FuncAnimation(
            self.fig, self.animate, interval=self.interval,
            blit=False, cache_frame_data=False)

        self.build()
        for s in self.entries.values():
            s.configure(command=self.on_param_change)

    # ---------- anty-lag ----------
    def on_canvas_configure(self, event):
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, lambda: self.canvas.resize(event))

    def on_window_configure(self, event):
        if event.widget is not self:
            return
        self._busy = True
        if self._busy_job is not None:
            self.after_cancel(self._busy_job)
        self._busy_job = self.after(150, self._unbusy)

    def _unbusy(self):
        self._busy = False

    def style_axes(self):
        for ax in self.fig.axes:
            ax.set_facecolor(BG)
            ax.title.set_color(FG)
            ax.tick_params(colors=FG)
            ax.xaxis.label.set_color(FG)
            ax.yaxis.label.set_color(FG)
            for sp in ax.spines.values():
                sp.set_color("#555555")

    # ---------- model ----------
    def read_params(self):
        return {k: clean(k, s.get()) for k, s in self.entries.items()}

    def build(self):
        self.model = SEIR(**self.read_params())
        field = self.model.get_field()

        self.fig.clear()
        self.axes = self.fig.subplots(2, 2)

        states = {
            "S": self.model.S_VAL,
            "E": self.model.E_VAL,
            "I": self.model.I_VAL,
            "R": self.model.R_VAL,
        }
        positions = {"S": (0, 0), "E": (0, 1), "I": (1, 0), "R": (1, 1)}

        self.images = {}
        for name, index in states.items():
            ax = self.axes[positions[name]]
            data = (field == index).astype(float)
            self.images[name] = plot_heatmap(
                data, ax=ax, cmap="inferno", vmin=0, vmax=1, title=name)

        self.fig.suptitle(self.model.info(), color=FG)
        self.style_axes()
        self.canvas.draw_idle()  

    def toggle(self):
        if self.running:
            self.running = False
            self.buttonRun.configure(text="Start")
        else:
            if self.model is None:
                self.build()
            self.running = True
            self.buttonRun.configure(text="Pauza")

    def reset(self):
        self.running = False
        self.buttonRun.configure(text="Start")
        self.build()

    def animate(self, _):
        if not self.running or self.model is None or self._busy:
            return []

        for _ in range(self.spf):
            self.model.step(self.dt)

        field = self.model.get_field()
        states = {
            "S": self.model.S_VAL,
            "E": self.model.E_VAL,
            "I": self.model.I_VAL,
            "R": self.model.R_VAL,
        }
        for name, index in states.items():
            self.images[name].set_data((field == index).astype(float))

        self.fig.suptitle(self.model.info(), color=FG)
        return list(self.images.values())

    def on_param_change(self, _=None):
        for name, vl in self.value_labels.items():
            vl.configure(text=fmt(name, clean(name, self.entries[name].get())))
        if self.running:
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(120, self.build)


if __name__ == "__main__":
    Window().mainloop()