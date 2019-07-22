import os
import glob
import logging
import pandas as pd
from pyunpack import Archive
import pyspectra

def recal(target_dir):
    files_status = {}
    for filename in glob.iglob(os.path.join(target_dir, '**/*'), recursive=True):
        try:
            spc = pyspectra.read_bwtek(filename)
            spc = spc[:,:,80:3010]
            pd.DataFrame({"wl": spc.wl, "spc": spc.spc.iloc[0,:].values}).to_csv(filename, header=False, index=False)
            files_status[filename] = True
        except Exception as e:
            files_status[filename] = False
            logging.error(e)
    return files_status

