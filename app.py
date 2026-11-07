import customtkinter as ctk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation

from models import SEIR
from plot import plot_heatmap

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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
    infectionFactor="Współczynnik infekcji (ɣ)",
    infectionPeroid="Okres zakaźności [dni] (β)",
    incubationPeroid="okres inkubacji [dni] (δ)",
    immunityPeroid="Czas odporności [dni] (ω)",
    lethality="Śmiertelność choroby (α)",
    naturalLethality="Śmiertelność naturalna [1/dzień] (μ)",
)

INT_PARAMS = {"S", "I", "R", "E"}
BG = "#242424"


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


class Window(ctk.CTk):
    def __init__(self, dt=0.1, steps_per_frame=5, interval=30):
        super().__init__()
        self.dt, self.spf, self.interval = dt, steps_per_frame, interval
        self.model = None
        self.im = None
        self.running = False
        self._job = None
        self._resize_job = None
        self._busy = False          # okno jest ruszane / skalowane
        self._busy_job = None
        self.title("SEIRS epidemic simulation")
        self.geometry("1150x720")
        self.init_window()

    def init_window(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel = ctk.CTkScrollableFrame(self, width=320, corner_radius=12,
                                       label_text="Parametry modelu")
        panel.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)

        self.entries = {}
        self.value_labels = {}
        for name, (val, lo, hi, step) in PARAMS.items():
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", pady=(6, 0))
            ctk.CTkLabel(row, text=LABELS[name], anchor="w").pack(side="left")
            vl = ctk.CTkLabel(row, text=fmt(name, val), anchor="e",
                              text_color=("#1f6aa5", "#5ab0ff"))
            vl.pack(side="right")

            s = ctk.CTkSlider(panel, from_=lo, to=hi,
                              number_of_steps=max(1, round((hi - lo) / step)))
            s.set(val)
            s.pack(fill="x", pady=(2, 4))
            self.entries[name] = s
            self.value_labels[name] = vl

        btns = ctk.CTkFrame(panel, fg_color="transparent")
        btns.pack(fill="x", pady=(14, 4))
        self.buttonRun = ctk.CTkButton(btns, text="Start", command=self.toggle)
        self.buttonRun.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.buttonReset = ctk.CTkButton(btns, text="Reset", command=self.reset,
                                         fg_color="transparent", border_width=2,
                                         text_color=("gray10", "gray90"))
        self.buttonReset.pack(side="left", expand=True, fill="x", padx=(4, 0))

        plot_frame = ctk.CTkFrame(self, corner_radius=12)
        plot_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        self.fig = Figure(figsize=(6, 5), facecolor=BG)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        widget = self.canvas.get_tk_widget()
        widget.configure(bg=BG, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=6, pady=6)

        # matplotlib domyślnie przerysowuje figurę przy KAŻDYM evencie Configure
        # -> zastępujemy to debounce'owanym resize
        widget.unbind("<Configure>")
        widget.bind("<Configure>", self.on_canvas_configure)
        # ruch/skalowanie okna -> chwilowo wstrzymaj animację
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

    # ---------- wygląd ----------
    def style_axes(self):
        fg = "#e0e0e0"
        self.ax.set_facecolor(BG)
        self.ax.title.set_color(fg)
        for a in self.fig.axes:                     # także colorbar
            a.tick_params(colors=fg)
            a.yaxis.label.set_color(fg)
            for sp in a.spines.values():
                sp.set_color("#555555")

    # ---------- model ----------
    def read_params(self):
        return {k: clean(k, s.get()) for k, s in self.entries.items()}

    def build(self):
        self.model = SEIR(**self.read_params())
        field = self.model.get_field()
        if self.im is None or not self.fig.axes:
            self.fig.clear()
            self.ax = self.fig.add_subplot(111)
            self.im = plot_heatmap(field, ax=self.ax, cmap="inferno")
            self.style_axes()
        else:
            plot_heatmap(field, im=self.im)
        self.ax.set_title(self.model.info())
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
        plot_heatmap(self.model.get_field(), im=self.im)
        self.ax.set_title(self.model.info())
        return [self.im]

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