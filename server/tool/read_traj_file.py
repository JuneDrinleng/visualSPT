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


if __name__ == "__main__":
    read_trackmate_csv("test_data\\traj\\trackmate-output-csv.csv")