import numpy as np
import pandas as pd
def read_trackmate_csv(file_path):
    """
    This function is to read the traj data output from Fiji TrackMate plugin
    """
    df=pd.read_csv(file_path)
    df = df.sort_values(by=['TRACK_ID', 'FRAME'])
    target_cols = ['POSITION_X', 'POSITION_Y']
    grouped = df.groupby('TRACK_ID')
    trajs_list = [group[target_cols].values for _, group in grouped]
    B = len(trajs_list) 
    max_len = max(len(t) for t in trajs_list)
    dimension = len(target_cols)
    result_array = np.full((B, max_len, dimension), np.nan)
    for i, traj in enumerate(trajs_list):
        current_len = len(traj)
        result_array[i, :current_len, :] = traj
    return result_array,B

def read_npy_traj(file_path):
    """
    This function is to read the traj data saved in npy format
    """
    data = np.load(file_path, allow_pickle=True)
    if data.ndim == 3 :
        B, max_len, dimension = data.shape
        if max_len<dimension:
            data = np.transpose(data, (0, 2, 1))
            B, max_len, dimension = data.shape
    elif data.ndim == 2:
        max_len, dimension = data.shape
        if max_len<dimension:
            data = np.transpose(data, (1, 0))
            data = np.expand_dims(data, axis=0)
            B,max_len, dimension = data.shape
        else:
            data = np.expand_dims(data, axis=0)
            B,max_len, dimension = data.shape
    return data,B

def read_npz_traj(file_path):
    """
    This function is used to read the trajectory from NPZ files.
    """
    npz = np.load(file_path, allow_pickle=True)
    keys = list(npz.keys())
    candidates = ['track', 'traj', 'trajs', 'tracks', 'trajectory','trajectories']

    # pick a sensible key: prefer keys containing candidate words (case-insensitive)
    selected_key = None
    for k in keys:
        kl = k.lower()
        if any(c in kl for c in candidates):
            selected_key = k
            break

    # fallback: if only one array, use it; otherwise find first array-like candidate
    if selected_key is None:
        if len(keys) == 1:
            selected_key = keys[0]
        else:
            for k in keys:
                arr = npz[k]
                if isinstance(arr, (list, tuple)) or getattr(arr, 'dtype', None) == object:
                    selected_key = k
                    break
                if hasattr(arr, 'ndim') and arr.ndim in (2, 3):
                    selected_key = k
                    break

    if selected_key is None:
        raise ValueError(f"No suitable trajectory array found in npz file. Keys: {keys}")

    arr = npz[selected_key]

    # Helper: convert a list/sequence of variable-length trajs to padded 3D array
    def _from_sequence(seq):
        trajs = [np.asarray(t) for t in seq]
        B = len(trajs)
        if B == 0:
            return np.empty((0, 0, 0)), 0
        # ensure each trajectory has shape (T, D)
        for i, t in enumerate(trajs):
            t = np.asarray(t)
            if t.ndim == 1:
                t = t.reshape(-1, 1)
            trajs[i] = t
        max_len = max(t.shape[0] for t in trajs)
        dimension = trajs[0].shape[1]
        result = np.full((B, max_len, dimension), np.nan)
        for i, t in enumerate(trajs):
            if t.shape[1] != dimension and t.shape[0] < t.shape[1]:
                t = t.T
            result[i, :t.shape[0], :t.shape[1]] = t
        return result, B

    # Handle object arrays / lists of trajectories
    if isinstance(arr, (list, tuple)) or getattr(arr, 'dtype', None) == object:
        return _from_sequence(arr)

    # Handle numpy arrays
    arr = np.asarray(arr)
    if arr.ndim == 3:
        B, max_len, dimension = arr.shape
        if max_len < dimension:
            arr = arr.transpose(0, 2, 1)
            B, max_len, dimension = arr.shape
        return arr, B
    elif arr.ndim == 2:
        max_len, dimension = arr.shape
        # if transposed (more columns than rows), transpose
        if max_len < dimension:
            arr = arr.T
            max_len, dimension = arr.shape
        arr = np.expand_dims(arr, axis=0)
        return arr, 1
    elif arr.ndim == 1:
        arr = arr.reshape(1, -1, 1)
        return arr, 1
    else:
        raise ValueError(f"Unhandled array shape for key '{selected_key}': {arr.shape}")

if __name__ == "__main__":
    # read_trackmate_csv("test_data\\traj\\trackmate-output-csv.csv")
    result,B=read_npz_traj("test_data\\traj\\vepinn-collect-npz.npz")
    pass