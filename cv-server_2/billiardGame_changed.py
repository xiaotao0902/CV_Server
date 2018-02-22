import cv2
import v4l2
from services import initialStateDetectionService, sendResultService
from config import config
import yolo_server
from fcntl import ioctl


class Game(object):
    def __init__(self, game_context):
        self.gameContext = game_context
        self.debug = False
        self.videoPath = None
        self.camera = None
        self.posFrame = None
        self.stillFrameCount = 0
        self.currentFrame = {
            'still': False,
            'content': None,
            'backup': None
        }
        self.result = None
        self.backgroundMOGForMovementDetection = None
        self.backgroundMOGForMovementDetectionMask = None
        self.movementDetectionStepCount = config.movementDetectionStepCount
        self.movementDetectionStep = config.movementDetectionStep
        self.movementAreaTH = config.movementAreaTH
        self.foundInitialState = False
        self.gameOn = False

    def enable_debug_mode(self):
        self.debug = True

    def set_camera_mode(self, mode, video_path=0):
        if mode == 'video':
            self.videoPath = video_path
        elif mode == 'camera':
            self.videoPath = 0
        return True

    def _configure_camera_size(self):
        print 'Configuring Camera Size ...'
        self.camera.set(3, config.imageOperatingSize[0])
        self.camera.set(4, config.imageOperatingSize[1])

    def _configure_camera_param(self):
        print 'Configuring Camera Param CONTRAST ...by song'
	self.camera.set(cv2.cv.CV_CAP_PROP_CONTRAST, 0.5)
	print 'Configuring Camera Param SATURATION ...by song'
	self.camera.set(cv2.cv.CV_CAP_PROP_SATURATION, 128)
	#print 'Configuring Camera Param EXPOSURE ...by song'
	#self.camera.set(cv2.cv.CV_CAP_PROP_EXPOSURE, 0)
	print 'Configuring Camera Param FOURCC ...by song'
	self.camera.set(cv2.cv.CV_CAP_PROP_FOURCC, 0.1)
        
    def _process_frame(self):
	print 'processing frame...'	
        self.result = yolo_server.predict(self.currentFrame['content'])
        result_img = self.currentFrame['content'].copy()
        for box in self.result:
            cv2.rectangle(result_img, (box['left'], box['top']), (box['right'], box['bottom']), (255, 255, 0))
        cv2.imshow('result', result_img)#---------------------lu
        print 'result is', self.result

    def _display_result(self):
        print self.result

    def _send_result(self):
        print 'about to send result', self.result
        sendResultService.send_result(self.result, self.gameContext)

    def _should_run_yolo(self):
        if self.movementDetectionStepCount % self.movementDetectionStep == 0:
            self.backgroundMOGForMovementDetection = cv2.BackgroundSubtractorMOG(history=10,
                                                                                 nmixtures=3,
                                                                                 backgroundRatio=0.6,
                                                                                 noiseSigma=20)
        if (self.currentFrame['content'] is not None) and (self.backgroundMOGForMovementDetection is not None):
            self.backgroundMOGForMovementDetectionMask = self.backgroundMOGForMovementDetection.apply(self.currentFrame['content'])
            contours, _ = cv2.findContours(image=self.backgroundMOGForMovementDetectionMask,
                                           mode=cv2.RETR_TREE,
                                           method=cv2.CHAIN_APPROX_SIMPLE)
            areas = 0
            for cnt in contours:
                areas = areas + cv2.contourArea(cnt)
            if areas <= self.movementAreaTH:
                self.stillFrameCount += 1
                if self.stillFrameCount == config.still_frame_count:
                    # print 'press anykey to process frame'
                    # cv2.waitKey()
                    return True
                else:
                    return False
            else:
                self.stillFrameCount = 0
                return False
        self.stillFrameCount = 0
        return False

	def _open_devices(self):
	    print 'Open camera devices ...'
	    import glob
	    if self.camera is None:
	        self.camera = [
	            open(device, 'rw')
	            for device in glob.glob('/dev/video*')]
	        assert self.camera, 'No video devices found.'
        print 'Device is opened', self.camera
	
	def valid_string(string):
	    for char in string:
	        if (ord(char) < 32 or 126 < ord(char)):
	            return False
	    return True
	def valid_capabilities(capabilities):
	    return capabilities & ~ (
	        v4l2.V4L2_CAP_VIDEO_CAPTURE |
	        v4l2.V4L2_CAP_VIDEO_OUTPUT |
	        v4l2.V4L2_CAP_VIDEO_OVERLAY |
	        v4l2.V4L2_CAP_VBI_CAPTURE |
	        v4l2.V4L2_CAP_VBI_OUTPUT |
	        v4l2.V4L2_CAP_SLICED_VBI_CAPTURE |
	        v4l2.V4L2_CAP_SLICED_VBI_OUTPUT |
	        v4l2.V4L2_CAP_RDS_CAPTURE |
	        v4l2.V4L2_CAP_VIDEO_OUTPUT_OVERLAY |
	        v4l2.V4L2_CAP_TUNER |
	        v4l2.V4L2_CAP_AUDIO |
	        v4l2.V4L2_CAP_RADIO |
	        v4l2.V4L2_CAP_READWRITE |
	        v4l2.V4L2_CAP_ASYNCIO |
	        v4l2.V4L2_CAP_STREAMING) == 0

	def _check_capability(self):
	    cap = v4l2.v4l2_capability()

	    ioctl(self.camera, v4l2.VIDIOC_QUERYCAP, cap)

	    assert 0 < len(cap.driver)
	    assert valid_string(cap.card)
	    # bus_info is allowed to be an empty string
	    assert valid_string(cap.bus_info)
	    assert valid_capabilities(cap.capabilities)
	    assert cap.reserved[0] == 0
	    assert cap.reserved[1] == 0
	    assert cap.reserved[2] == 0
	    assert cap.reserved[3] == 0

#		print 'Driver Name:%s\nCard Name:%s\nBus info:%s\nCapabilities:%u\n' cap.driver,cap.card,cap.bus_info,cap.capabilities

	def _configure_format(self):
	    print 'Check format description ...'
	    fmtdesc = v4l2.v4l2_fmtdesc()
	    fmtdesc.index = 0
	    fmtdesc.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
	    print 'Support format:'
	    while True:
	    	ret, ioctl(self.camera, VIDIOC_ENUM_FMT, fmtdesc)
	    	if ret:
	    		print fmtdesc.index, fmtdesc.description, fmtdesc.pixelformat
	    		fmtdesc.index = fmtdesc.index + 1
	    	else:
	    		break
	    print 'Set video format ...'
	    video_format = v4l2.v4l2_format()
	    video_format.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
	    video_format.fmt.pix.width = config.imageOperatingSize[0]
	    video_format.fmt.pix.height = config.imageOperatingSize[1]
	    video_format.fmt.pix.pixelfformat = V4L2_PIX_FMT_YUYV
	    video_format.fmt.pix.field = V4L2_FIELD_INTERLACED

    	ret, ioctl(self.camera, VIDIOC_S_FMT, video_format)
    	if ret:
    		print fmtdesc.index, fmtdesc.description, fmtdesc.pixelformat

def _get_device_controls(self):
    # original enumeration method
    queryctrl = v4l2.v4l2_queryctrl(v4l2.V4L2_CID_BASE)

    while queryctrl.id < v4l2.V4L2_CID_LASTP1:
        try:
            ioctl(self.camera, v4l2.VIDIOC_QUERYCTRL, queryctrl)
        except IOError, e:
            # this predefined control is not supported by this device
            assert e.errno == errno.EINVAL
            queryctrl.id += 1
            continue
        yield queryctrl
        queryctrl = v4l2.v4l2_queryctrl(queryctrl.id + 1)

    queryctrl.id = v4l2.V4L2_CID_PRIVATE_BASE
    while True:
        try:
            ioctl(self.camera, v4l2.VIDIOC_QUERYCTRL, queryctrl)
        except IOError, e:
            # no more custom controls available on this device
            assert e.errno == errno.EINVAL
            break
        yield queryctrl
        queryctrl = v4l2.v4l2_queryctrl(queryctrl.id + 1)


    def _init_camera(self):
        print 'Initialize camera devices ...'
        self._open_devices()

    def start(self):
        self.gameOn = True
        self._init_camera()
        while self.gameOn:
            ret, self.currentFrame['content'] = self.camera.read()

            if ret:
                self.currentFrame['content'] = cv2.resize(src=self.currentFrame['content'], dsize=config.imageOperatingSize)
                if self._should_run_yolo():
                    self._process_frame()
                    if not self.foundInitialState:
                        self.foundInitialState = initialStateDetectionService.is_initial_state(self.result)
                    if self.foundInitialState:
                        self._send_result()
		    else:	
			print 'not initial state yet' 
                cv2.imshow('Stream', self.currentFrame['content'])#--------------LU
                cv2.waitKey(10)
                self.movementDetectionStepCount += 1
            else:
                self.camera.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, self.posFrame - 1)
                cv2.waitKey(200)
        cv2.destroyAllWindows()
        cv2.VideoCapture(self.videoPath).release()

    def stop(self):
        self.gameOn = False
