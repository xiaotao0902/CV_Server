import sys
sys.path.append('/usr/local/lib/python2.7/dist-packages/')

import pyyolo
import numpy as np
import cv2

darknet_path = './darknet'
data_cfg = 'deployment/easy.data'
cfg_file = 'deployment/easy-tiny.cfg'
weight_file = 'deployment/easy-tiny.backup'
thresh = 0.24
hier_thresh = 0.5

pyyolo.init(darknet_path, data_cfg, cfg_file, weight_file)


def predict(img):
    img = img.transpose(2, 0, 1)
    c, h, w = img.shape[0], img.shape[1], img.shape[2]
    # print w, h, c
    data = img.ravel() / 255.0
    data = np.ascontiguousarray(data, dtype=np.float32)
    outputs = pyyolo.detect(w, h, c, data, thresh, hier_thresh)
    return outputs


def clean_up():
    pyyolo.cleanup()

