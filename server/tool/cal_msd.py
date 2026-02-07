import numpy as np
def eamsd_cal(X, t0: int = 0, lags=None, center: bool = False):
    """
    Parameters
    ----------
    X : ndarray, shape (B, L, D) N:traj_len
    t0 : int, default 0, initial time frame index
    lags : 1D array-like of int, optional
    center : bool, default False, whether to do "detrended centering": E[||Δr||^2] - ||E[Δr]||^2

    Returns
    -------
    msd : ndarray, shape (lags_len,)
    """
    X = np.asarray(X)
    X = X.transpose(0, 2, 1)  # (B, L, D) into (B, D, L)
    B, D, T = X.shape
    # reasonable default: at least include lag 0, and up to T//4 (exclusive stop)
    if lags is None:
        max_lag = max(1, T // 4)
        lags = np.arange(0, max_lag, dtype=int)
    else:
        lags = np.asarray(lags, dtype=int)
    # keep only valid lag indices (>=0 and within bounds)
    if lags.size == 0:
        return np.array([]), np.array([]), np.array([])
    valid_mask = (lags >= 0) & ((t0 + lags) < T)
    lags = lags[valid_mask]
    if lags.size == 0:
        return np.array([]), np.array([]), np.array([])
    r0 = X[:, :, [t0]]
    Xt = X[:, :, t0 + lags]
    disp = Xt - r0
    # disp shape: (B, D, len(lags)) -> compute squared displacement per lag
    msd = np.mean(np.einsum('ndl,ndl->nl', disp, disp), axis=0)  # (L,)
    if center:
        mean_disp = disp.mean(axis=0)                 # (d, L)
        drift_term = np.einsum('dl,dl->l', mean_disp, mean_disp)
        msd = msd - drift_term
        msd = np.maximum(msd, 0.0)
    tamsd_arr = np.zeros((B, len(lags)))
    for i in range(B):
        try:
            tamsd_spec = tamsd_cal(X[i].transpose(1, 0), max_lag=len(lags))
        except Exception:
            tamsd_spec = np.zeros(len(lags))
        # ensure length
        if len(tamsd_spec) < len(lags):
            tmp = np.zeros(len(lags))
            tmp[:len(tamsd_spec)] = tamsd_spec
            tamsd_spec = tmp
        tamsd_arr[i, :] = tamsd_spec[:len(lags)]
    # compute mean/std safely
    if tamsd_arr.size == 0:
        tamsd_mean = np.array([])
        tamsd_std = np.array([])
    else:
        tamsd_mean = tamsd_arr.mean(axis=0)
        tamsd_std = tamsd_arr.std(axis=0)
    eamsd = msd
    # Return per-trajectory TAMSD array as fourth element to allow callers
    # to reuse individual TAMSD series without recomputing.
    return eamsd, tamsd_mean, tamsd_std, tamsd_arr

def tamsd_cal(trajectory_input, max_lag=None):
    """
    calculate time-averaged mean square displacement
    :param trajectory_input: numpy array of shape (L, D), where L is traj_len, D is dimension
    :param max_lag: maximum lag time to calculate MSD, default is traj_len//4
    :return: msd: numpy array of shape (max_lag,)
    """
    trajectory = np.asarray(trajectory_input)
    trajectory = trajectory.transpose(1, 0)  # (L, D) into (D, L)
    traj_len = trajectory.shape[1]
    if max_lag is None:
        max_lag = max(1, traj_len // 4)
    # ensure integer and at least 1
    max_lag = int(max(1, max_lag))
    msd = np.zeros(max_lag)
    for t in range(1, max_lag):
        displacements = trajectory[:, t:] - trajectory[:, :-t]
        # handle case where displacements may be empty
        if displacements.size == 0:
            msd[t] = 0.0
            continue
        dx2 = displacements[0] ** 2
        dy2 = displacements[1] ** 2
        msd[t] = np.mean(dx2 + dy2)
    return msd