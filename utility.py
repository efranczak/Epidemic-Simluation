from matplotlib import pyplot as plt
from matplotlib.animation import FuncAnimation

from models import Model
from plot import plot_heatmap


def run_realtime(model:Model, dt=0.1, steps_per_frame=5, interval=30, cmap="inferno", v_min=None, v_max=None, title="Symulacja"):
    fig, ax = plt.subplots()
    im = plot_heatmap(model.get_field(), ax=ax, cmap=cmap, vmin=v_min, vmax=v_max, title=title)

    def update(_):
        for _ in range(steps_per_frame):
            model.step(dt)
        plot_heatmap(model.get_field(), im=im, vmin=v_min, vmax=v_max)
        ax.set_title(f"{title}  {model.info()}")
        return (im,)

    anim = FuncAnimation(fig, update, interval=interval, blit=False, cache_frame_data=False)
    plt.show()
    return anim