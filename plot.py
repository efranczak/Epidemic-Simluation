import matplotlib.pyplot as plt



def plot_heatmap(data, ax=None, im=None, cmap="viridis", vmin=None, vmax=None, title=None):
    """Rysuje heatmapę. Jeśli podasz `im`, tylko aktualizuje dane (szybko, do animacji)."""
    if im is not None:
        im.set_data(data)
        if vmin is None and vmax is None:
            im.set_clim(data.min(), data.max())
        return im

    if ax is None:
        _, ax = plt.subplots()
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, origin="lower", interpolation="nearest")
    if title:
        ax.set_title(title)
    plt.colorbar(im, ax=ax)
    return im
