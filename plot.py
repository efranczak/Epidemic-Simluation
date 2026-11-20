import matplotlib.pyplot as plt



def plot_heatmap(data, ax=None, im=None, cmap="viridis",
                 vmin=None, vmax=None, title=None):

    if im is not None:
        im.set_data(data)
        return im

    if ax is None:
        _, ax = plt.subplots()

    im = ax.imshow(
        data,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        origin="lower",
        interpolation="nearest"
    )

    if title:
        ax.set_title(title)

    return im
