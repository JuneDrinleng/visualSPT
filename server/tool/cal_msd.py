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
    msd : ndarray, shape (L,)
    """
    X = np.asarray(X)
    X=X.transpose(0, 2, 1)  # (B, L, D) into (B, D, L)
    B, D, T = X.shape
    if lags is None:
        lags = np.arange(0, T/4, dtype=int)
    else:
        lags = np.asarray(lags, dtype=int)
    r0 = X[:, :, [t0]]
    Xt = X[:, :, t0 + lags]
    disp = Xt - r0
    msd = np.mean(np.einsum('ndl,ndl->nl', disp, disp), axis=0)  # (L,)
    if center:
        mean_disp = disp.mean(axis=0)                 # (d, L)
        drift_term = np.einsum('dl,dl->l', mean_disp, mean_disp)
        msd = msd - drift_term
        msd = np.maximum(msd, 0.0)
    return msd

def tamsd_cal(trajectory, max_lag=None):
    """
    calculate time-averaged mean square displacement
    :param trajectory: numpy array of shape (D, N), where N is traj_len, D is dimension
    :param max_lag: maximum lag time to calculate MSD, default is traj_len//4
    :return: msd: numpy array of shape (max_lag,)
    """
    traj_len = trajectory.shape[1]
    if max_lag is None:
        max_lag = traj_len//4
    msd = np.zeros(max_lag)
    for t in range(1, max_lag):
        displacements = trajectory[:, t:] - trajectory[:, :-t]
        dx2 = displacements[0]**2
        dy2 = displacements[1]**2
        msd[t] = np.mean(dx2+dy2)
    return msd