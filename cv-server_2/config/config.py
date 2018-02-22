import v4l2
# for initial state detection
initial_bounding_box_limit = 5000
initial_ball_count_limit = 0

# send result
url = 'http://0.0.0.0:8080/BallMatchService/bs/game/info'

# Camera parameters
CameraDevice = '/dev/video0'
FormatPixelformat = v4l2.V4L2_PIX_FMT_YUYV
FormatField = v4l2.V4L2_FIELD_INTERLACED
ControlBrightness = 156
ControlContrast = 156
ControlSaturation = 100
ControlGain = 5
ControlWhiteBalanceAuto = 0
ControlWhiteBalanceTemperature = 3735
ControlSharpness = 166
ControlBacklightCompensation = 0
ControlExposureAuto = 1
ControlExposureAbsolute = 256
ControlFocusAuto = 0
ControlFocusAbsolute = 0
ControlZoomAbsolute = 100
V4l2ReqBuffersCount = 4


# run yolo related
still_frame_count = 10
imageOperatingSize = (1024, 576)

# movement detection
movementDetectionStepCount = 10
movementDetectionStep = 3
movementAreaTH = 10.0

# task
num_class = 16
