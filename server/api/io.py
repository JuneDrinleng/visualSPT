def read_trajectory_from_path(file_path, api):
    """Given a file path and an Api instance (with read_* methods assigned), return (data, count)."""
    if file_path.endswith('.csv'):
        return api.read_trackmate_csv(file_path)
    elif file_path.endswith('.npy'):
        return api.read_npy_traj(file_path)
    elif file_path.endswith('.npz'):
        return api.read_npz_traj(file_path)
    else:
        raise ValueError("Unsupported file type")
