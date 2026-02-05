import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap
def plot_traj_beauty(traj,dt=0.01, save_path=None):
    """
    :param traj: shape (B,L,D)
    :param dt: frame time step
    :param save_path: eg. "results/visualization/traj_sample.png"
    """
    pastel_deeper = LinearSegmentedColormap.from_list('pastel_deeper', ['#D9ECFF', '#AEEEDC', '#FFE89A'])
    B, L, D = traj.shape
    def set_square_limits(ax_obj, x_data, y_data):
        x_mid = 0.5 * (x_data.min() + x_data.max())
        y_mid = 0.5 * (y_data.min() + y_data.max())
        span = max(x_data.max() - x_data.min(), y_data.max() - y_data.min())
        span *= 1.1 
        half_span = span / 2
        ax_obj.set_xlim(x_mid - half_span, x_mid + half_span)
        ax_obj.set_ylim(y_mid - half_span, y_mid + half_span)
    time_axis = np.arange(L) * dt
    vmin, vmax = time_axis.min(), time_axis.max()
    traj_origin_sample = traj[np.random.randint(0, B)]
    origin_x = traj_origin_sample[:, 0]
    origin_y = traj_origin_sample[:, 1]
    points1 = np.array([origin_x, origin_y]).T.reshape(-1, 1, 2)
    segments1 = np.concatenate([points1[:-1], points1[1:]], axis=1)
    fig, ax = plt.subplots() 
    lc1 = LineCollection(segments1, cmap=pastel_deeper, linewidth=2, alpha=1.0)
    lc1.set_array(time_axis) 
    lc1.set_clim(vmin=vmin, vmax=vmax) 
    ax.add_collection(lc1)
    ax.set_box_aspect(1)
    set_square_limits(ax, origin_x, origin_y)
    cbar1 = fig.colorbar(lc1, ax=ax, fraction=0.046, pad=0.04)
    cbar1.set_label('Time (s)')
    plt.tight_layout()
    if save_path is not None:
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
    else:
        plt.show()
    pass