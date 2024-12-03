import numpy as np
import matplotlib.pyplot as plt



save_dir = "C:/Users/maxst/VS-data/"
metadata = np.load(save_dir+'M240416_SPK_IDR3_FB1_metadata.npy', allow_pickle=True).item()
num_frames = metadata['num_frames']
frame_width = metadata['frame_width']
frame_height = metadata['frame_height']
data_type = metadata['data_type']
frame_timestamps = metadata['frame_timestamps']
sys_timestamps = metadata['sys_clock_timestamps']

print(num_frames, len(frame_timestamps))    
plt.plot(np.diff(frame_timestamps)[:])
plt.show()