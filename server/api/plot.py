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

    try:
        arr = np.array(traj)
        if arr.ndim >= 2 and arr.shape[1] >= 2:
            return arr[:, 0], arr[:, 1]
    except Exception:
        pass
    return [], []


def generate_plot(plt, np, x, y, title='Trajectory Visualization', scale=1.0, zero_start=False, x_unit="px", y_unit="px", save_path=None, custom_title="", show_markers=True, show_title=True, show_axis_labels=True, show_grid=True, show_colorbar=True, show_ticks=True, show_border=True):
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
    dpi = 80 if not save_path else 150
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
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

        if show_colorbar:
            cbar = fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Time (Frame)')

        if not show_ticks:
            ax.set_xticks([])
            ax.set_yticks([])

        if not show_border:
            ax.axis('off')

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
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return "data:image/png;base64," + img_base64

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


def generate_msd_plot(plt, np, lags, eamsd=None, tamsd=None, tamsd_mean=None, tamsd_std=None, title='MSD Visualization', x_unit="frame", y_unit="unit", save_path=None, custom_title="", show_legend=True, show_title=True, show_axis_labels=True, plot_eamsd=True, plot_tamsd=True, plot_tamsd_mean=True):
    c_red_dark  = "#BA0E05"  
    c_red_base  = "#E04F5F"  
    c_red_light = "#F4A3AE"  
    c_red_bg    = "#FDECEC"  

    c_blue_dark  = "#4A90E2"  
    c_blue_base  = "#7CB9E8"  
    c_blue_light = "#B3D1F5"  
    c_blue_bg    = "#EAF4FC"  

    c_orange_dark  = "#E68A00"  
    c_orange_base  = "#F7B267"  
    c_orange_light = "#FAD9B3" 
    c_orange_bg    = "#FEF5EA" 

    c_green_dark  = "#28C76F"  
    c_green_base  = "#9BE7C4"  
    c_green_light = "#CDF3E1"  
    c_green_bg    = "#E9F9F0"  

    c_gray_900 = "#1F2937"  
    c_gray_700 = "#4B5563"  
    c_gray_500 = "#9CA3AF"  
    c_gray_300 = "#D1D5DB"  
    c_gray_100 = "#F3F4F6"  
    c_white    = "#FFFFFF"  

    plt.close('all')

    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    buf = io.BytesIO()

    try:
        has_any = False

        if plot_eamsd and eamsd is not None and len(eamsd) > 0:
            lags_e = np.asarray(lags, dtype=float)[:len(eamsd)]
            ax.loglog(lags_e, eamsd, color=c_orange_dark, lw=2.2, label='EAMSD')
            has_any = True

        if plot_tamsd and tamsd is not None and len(tamsd) > 0:
            lags_t =lags_e
            ax.loglog(lags_t, tamsd[:len(eamsd)], color=c_green_dark, lw=2.2, label='TAMSD')
            has_any = True

        tamsd_fill_handle = None
        if plot_tamsd_mean and tamsd_mean is not None and len(tamsd_mean) > 0:
            lags_tm = lags_e

            pos_mask = lags_tm >= 0
            if np.any(pos_mask):
                lags_pos = lags_tm[pos_mask]
                mean_pos = np.asarray(tamsd_mean, dtype=float)[pos_mask]

                if tamsd_std is not None and len(tamsd_std) == len(tamsd_mean):
                    std_pos = np.asarray(tamsd_std, dtype=float)[pos_mask]
                    lower = mean_pos - std_pos
                    upper = mean_pos + std_pos

                    lower = np.where(lower <= 0, 1e-12, lower)
                    try:
                        tamsd_fill_handle = ax.fill_between(lags_pos, lower, upper, color=c_green_base, alpha=0.7, label='TAMSD ± std')
                    except Exception:
                        tamsd_fill_handle = None
                else:
                    tamsd_fill_handle = None
                has_any = True

        if not has_any:
            return ""

        try:
            vals = []
            if plot_eamsd and eamsd is not None and len(eamsd) > 0:
                arr = np.asarray(eamsd, dtype=float).ravel()
                vals.append(arr)
            if plot_tamsd and tamsd is not None and len(tamsd) > 0:
                arr = np.asarray(tamsd, dtype=float).ravel()
                vals.append(arr)
            if tamsd_mean is not None and len(tamsd_mean) > 0:
                arr = np.asarray(tamsd_mean, dtype=float).ravel()
                vals.append(arr)

            if tamsd_mean is not None and tamsd_std is not None and len(tamsd_std) == len(tamsd_mean):
                tm = np.asarray(tamsd_mean, dtype=float)
                ts = np.asarray(tamsd_std, dtype=float)
                vals.append((tm + ts).ravel())

            if vals:
                concat = np.concatenate(vals)

                mask = np.isfinite(concat) & (concat > 1e-12)
                concat = concat[mask]
                if concat.size > 0:
                    ymin = float(concat.min())
                    ymax = float(concat.max())
                    if np.isfinite(ymin) and np.isfinite(ymax) and ymin > 0 and ymax > 0:

                        ax.set_ylim(ymin / 2.0, ymax * 2.0)
        except Exception:
            pass

        if show_title:
            final_title = custom_title if custom_title.strip() else title
            ax.set_title(final_title)

        if show_axis_labels:
            ax.set_xlabel(f"Lag ({x_unit})")
            ax.set_ylabel(f"MSD ({y_unit})")
        else:
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.set_xticks([])
            ax.set_yticks([])

        if show_legend:
            try:
                from matplotlib.patches import Patch
                import matplotlib.collections as mcollections

                handles, labels = ax.get_legend_handles_labels()
                new_handles = []
                new_labels = []
                for h, l in zip(handles, labels):
                    try:
                        if isinstance(h, mcollections.PolyCollection):
                            fc = h.get_facecolor()
                            if hasattr(fc, '__len__') and len(fc) > 0:
                                rgba = fc[0]

                                rgb = tuple(rgba[:3]) if len(rgba) >= 3 else tuple(rgba)
                                alpha = float(rgba[3]) if len(rgba) > 3 else None
                                new_handles.append(Patch(facecolor=rgb, edgecolor='none', alpha=alpha, label=l))
                            else:
                                new_handles.append(h)
                        else:
                            new_handles.append(h)
                    except Exception:
                        new_handles.append(h)
                    new_labels.append(l)
                ax.legend(new_handles, new_labels, loc='best')
            except Exception:
                ax.legend(loc='best')

        ax.grid(True, linestyle='--', alpha=0.25)

        if save_path:
            fmt = 'svg'
            if save_path.lower().endswith('.png'):
                fmt = 'png'
            elif save_path.lower().endswith('.pdf'):
                fmt = 'pdf'
            fig.savefig(save_path, format=fmt, bbox_inches='tight', dpi=300)
            return "saved"
        else:
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            return "data:image/png;base64," + img_base64
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Plot error (msd): {e}")
        return ""
    finally:
        plt.close(fig)
        buf.close()

    if zero_start:
        x = x - x[0]
        y = y - y[0]
    if scale != 1.0 and scale != 0:
        x = x * scale
        y = y * scale

    try:
        from matplotlib.collections import LineCollection
        import matplotlib.animation as animation

        L = len(x)
        if trail_len and trail_len > 0:
            trail_len = min(trail_len, L)
        else:
            trail_len = max(1, L // 2)
        try:
            fps = int(fps)
        except Exception:
            fps = 20

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

        ax.set_xlim(-limit * 1.05, limit * 1.05)
        ax.set_ylim(-limit * 1.05, limit * 1.05)
        ax.set_aspect('equal')
        ax.axis('off')
        if show_grid:
            ax.axhline(0, color='gray', alpha=0.3, lw=1, linestyle='--')
            ax.axvline(0, color='gray', alpha=0.3, lw=1, linestyle='--')

        if show_axis_labels:
            tick_val = limit
            fmt_pos = f'{tick_val:.2f}'
            fmt_neg = f'-{tick_val:.2f}'
            label_style = dict(fontsize=7, color='gray', alpha=0.6)
            offset = limit * 0.04

            tick_len = limit * 0.025
            tick_style = dict(color='gray', alpha=0.8, lw=1.5)

            ax.plot([limit, limit], [-tick_len, tick_len], **tick_style)
            ax.plot([-limit, -limit], [-tick_len, tick_len], **tick_style)
            ax.text(limit, -offset, f'{fmt_pos} {x_unit}', ha='center', va='top', **label_style)
            ax.text(-limit, -offset, f'{fmt_neg} {x_unit}', ha='center', va='top', **label_style)

            ax.plot([-tick_len, tick_len], [limit, limit], **tick_style)
            ax.plot([-tick_len, tick_len], [-limit, -limit], **tick_style)
            ax.text(-offset, limit, f'{fmt_pos} {y_unit}', ha='right', va='center', **label_style)
            ax.text(-offset, -limit, f'{fmt_neg} {y_unit}', ha='right', va='center', **label_style)

        particle, = ax.plot([], [], 'o', color='#ef4444', markeredgecolor='white', markeredgewidth=1.5, markersize=8, zorder=10)
        lc = LineCollection([], cmap='coolwarm', linewidths=3, capstyle='round', norm=plt.Normalize(0, 1))
        ax.add_collection(lc)

        if show_timebar and ax_bar is not None:
            norm = Normalize(vmin=0, vmax=trail_len)
            cb = ColorbarBase(ax_bar, cmap=plt.cm.coolwarm, norm=norm, orientation='horizontal')
            cb.set_ticks([])
            cb.set_label('')
            cb.outline.set_linewidth(0.6)
            cb.outline.set_edgecolor('#aaa')

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
