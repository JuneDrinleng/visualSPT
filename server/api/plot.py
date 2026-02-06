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
            ax.axhline(0, color='gray', alpha=0.3, lw=1, linestyle='--')
            ax.axvline(0, color='gray', alpha=0.3, lw=1, linestyle='--')
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


def generate_activation_plot(plt, np, x, y, title='Activation Visualization', scale=1.0, fps=20, trail_len=0, zero_start=False, x_unit="px", y_unit="px", save_path=None, custom_title="", show_timebar=True, show_title=True, show_axis_labels=True, show_grid=True):
    """A variant of trajectory plot suitable for dynamic/activation visualization.
    This renders the trajectory as colored scatter points with a fading trail.
    """
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

    # Implement dynamic-style plotting similar to plot_traj_dynamic: produce a GIF
    try:
        from matplotlib.collections import LineCollection
        import matplotlib.animation as animation

        # trail length and fps defaults
        L = len(x)
        if trail_len and trail_len > 0:
            trail_len = min(trail_len, L)
        else:
            trail_len = max(1, L // 2)
        try:
            fps = int(fps)
        except Exception:
            fps = 20

        # figure setup: center around origin similar to attachment
        max_abs_x = np.max(np.abs(x))
        max_abs_y = np.max(np.abs(y))
        limit = max(max_abs_x, max_abs_y) * 1.1

        if show_timebar:
            from matplotlib.colorbar import ColorbarBase
            from matplotlib.colors import Normalize
            import matplotlib.gridspec as gridspec

            fig = plt.figure(figsize=(5, 5.5), dpi=100)
            gs = gridspec.GridSpec(2, 1, height_ratios=[30, 1], hspace=0.08, bottom=0.05, top=0.95)
            ax = fig.add_subplot(gs[0])
            ax_bar = fig.add_subplot(gs[1])
        else:
            fig, ax = plt.subplots(figsize=(5, 5), dpi=100)
            ax_bar = None

        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect('equal')
        ax.axis('off')
        if show_grid:
            ax.axhline(0, color='gray', alpha=0.3, lw=1, linestyle='--')
            ax.axvline(0, color='gray', alpha=0.3, lw=1, linestyle='--')

        if show_axis_labels:
            fmt = f'{limit:.2f}'
            label_style = dict(fontsize=7, color='gray', alpha=0.6, ha='center', va='center')
            # X axis labels (left / right)
            ax.text(limit * 0.95, 0, f'{fmt} {x_unit}', ha='right', va='bottom', **{k: v for k, v in label_style.items() if k not in ('ha', 'va')})
            ax.text(-limit * 0.95, 0, f'-{fmt} {x_unit}', ha='left', va='bottom', **{k: v for k, v in label_style.items() if k not in ('ha', 'va')})
            # Y axis labels (top / bottom)
            ax.text(0, limit * 0.95, f'{fmt} {y_unit}', ha='left', va='top', **{k: v for k, v in label_style.items() if k not in ('ha', 'va')})
            ax.text(0, -limit * 0.95, f'-{fmt} {y_unit}', ha='left', va='bottom', **{k: v for k, v in label_style.items() if k not in ('ha', 'va')})

        particle, = ax.plot([], [], 'o', color='#ef4444', markeredgecolor='white', markeredgewidth=1.5, markersize=8, zorder=10)
        lc = LineCollection([], cmap='coolwarm', linewidths=3, capstyle='round', norm=plt.Normalize(0, 1))
        ax.add_collection(lc)

        # Static colorbar showing trail length range (blue → red)
        if show_timebar and ax_bar is not None:
            norm = Normalize(vmin=0, vmax=trail_len)
            cb = ColorbarBase(ax_bar, cmap=plt.cm.coolwarm, norm=norm, orientation='horizontal')
            cb.set_ticks([])
            cb.set_label('')
            cb.outline.set_linewidth(0.6)
            cb.outline.set_edgecolor('#aaa')
            # Label just above the colorbar
            ax_bar.text(0.5, 1.15, f'Trail: {trail_len} frames', transform=ax_bar.transAxes,
                        ha='center', va='bottom', fontsize=7, fontweight='semibold',
                        color='#000', fontstyle='italic')

        def update(frame):
            current_x = x[frame]
            current_y = y[frame]
            particle.set_data([current_x], [current_y])

            start = max(0, frame - trail_len)
            end = frame + 1
            if end - start > 1:
                xs = x[start:end]
                ys = y[start:end]
                points = np.array([xs, ys]).T.reshape(-1, 1, 2)
                segments = np.concatenate([points[:-1], points[1:]], axis=1)
                lc.set_segments(segments)
                color_array = np.linspace(0, 1, len(segments))
                lc.set_array(color_array)
                lc.set_clim(0, 1)
            else:
                lc.set_segments([])

            return [particle, lc]

        ani = animation.FuncAnimation(fig, update, frames=range(L), interval=1000 / fps, blit=True)

        # if a save path is provided, save to it; otherwise save to a temporary GIF and return data URL
        if save_path:
            try:
                ani.save(save_path, writer='pillow', fps=fps)
                return "saved"
            except Exception:
                return ""
        else:
            import tempfile, os
            tmp = None
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.gif')
                tmp.close()
                ani.save(tmp.name, writer='pillow', fps=fps)
                with open(tmp.name, 'rb') as f:
                    data = f.read()
                b64 = base64.b64encode(data).decode('utf-8')
                return 'data:image/gif;base64,' + b64
            except Exception:
                return ""
            finally:
                try:
                    if tmp is not None:
                        os.unlink(tmp.name)
                except Exception:
                    pass
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Plot error (activation): {e}")
        try:
            plt.close(fig)
        except Exception:
            pass
        return ""
