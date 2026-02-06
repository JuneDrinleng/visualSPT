import io
import base64


def extract_xy(traj, pd, np):
    if pd is not None and isinstance(traj, pd.DataFrame):
        if 'POSITION_X' in traj.columns and 'POSITION_Y' in traj.columns:
            return traj['POSITION_X'].values, traj['POSITION_Y'].values
        elif 'x' in traj.columns and 'y' in traj.columns:
            return traj['x'].values, traj['y'].values
    if np is not None and isinstance(traj, np.ndarray):
        if traj.ndim >= 2 and traj.shape[1] >= 2:
            return traj[:, 0], traj[:, 1]
    # try sequence
    try:
        arr = np.array(traj)
        if arr.ndim >= 2 and arr.shape[1] >= 2:
            return arr[:, 0], arr[:, 1]
    except Exception:
        pass
    return [], []


def generate_plot(plt, np, x, y, title='Trajectory Visualization', scale=1.0, zero_start=False, x_unit="px", y_unit="px", save_path=None, custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True):
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LinearSegmentedColormap

    plt.close('all')

    if not np.isfinite(x).all() or not np.isfinite(y).all():
        valid_mask = np.isfinite(x) & np.isfinite(y)
        x = x[valid_mask]
        y = y[valid_mask]

    if len(x) < 2:
        return ""

    if zero_start:
        x = x - x[0]
        y = y - y[0]
    if scale != 1.0 and scale != 0:
        x = x * scale
        y = y * scale

    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    time_axis = np.arange(len(x))

    figsize = (10, 8) if not save_path else (12, 10)
    fig, ax = plt.subplots(figsize=figsize)
    buf = io.BytesIO()

    try:
        pastel_deeper = LinearSegmentedColormap.from_list('pastel_deeper', ['#D9ECFF', '#AEEEDC', '#FFE89A'])

        lc = LineCollection(segments, cmap=pastel_deeper, linewidth=2, alpha=1.0)
        lc.set_array(time_axis)
        lc.set_clim(vmin=time_axis.min(), vmax=time_axis.max())
        ax.add_collection(lc)

        x_min, x_max = x.min(), x.max()
        y_min, y_max = y.min(), y.max()
        x_mid = 0.5 * (x_min + x_max)
        y_mid = 0.5 * (y_min + y_max)
        span_x = x_max - x_min
        span_y = y_max - y_min
        span = max(span_x, span_y)
        if span == 0:
            span = 1.0
        span *= 1.1
        half_span = span / 2
        if np.isnan(half_span) or np.isinf(half_span):
            half_span = 1.0
        ax.set_xlim(x_mid - half_span, x_mid + half_span)
        ax.set_ylim(y_mid - half_span, y_mid + half_span)
        ax.set_box_aspect(1)

        if show_markers:
            ax.plot(x[0], y[0], marker='o', color='#D9ECFF', markeredgecolor='gray', markersize=8, label='Start')
            ax.plot(x[-1], y[-1], marker='*', color='#FFE89A', markeredgecolor='gray', markersize=12, label='End')

        if show_title:
            final_title = custom_title if custom_title.strip() else title
            ax.set_title(final_title)

        if show_axis_labels:
            ax.set_xlabel(f"X ({x_unit})")
            ax.set_ylabel(f"Y ({y_unit})")

        if show_grid:
            ax.grid(True, linestyle='--', alpha=0.3)
        else:
            ax.grid(False)

        cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Time (Frame)')

        if show_markers:
            ax.legend(loc='upper right')

        if save_path:
            fmt = 'svg'
            if save_path.lower().endswith('.png'):
                fmt = 'png'
            elif save_path.lower().endswith('.pdf'):
                fmt = 'pdf'
            fig.savefig(save_path, format=fmt, bbox_inches='tight', dpi=300)
            return "saved"
        else:
            fig.savefig(buf, format='svg', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return "data:image/svg+xml;base64," + img_base64

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Plot error: {e}")
        return ""
    finally:
        plt.close(fig)
        buf.close()
