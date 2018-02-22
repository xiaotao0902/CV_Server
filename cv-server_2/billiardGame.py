import mmap
import os
import cv2
from services import initialStateDetectionService, sendResultService
from config import config
import yolo_server
import v4l2
import fcntl
import time
import numpy

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
        self._buffers = []
        self._mmaps = []
        self.sizeimage = 0
        self.CtrlId = 0
        self.CtrlValue = 0

    def enable_debug_mode(self):
        self.debug = True

    def set_camera_mode(self, mode, video_path=0):
        if mode == 'video':
            self.videoPath = video_path
        elif mode == 'camera':
            self.videoPath = 0
        return True

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

    def _handle_frame(self):
		dqbuf = v4l2.v4l2_buffer()
		dqbuf.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		dqbuf.memory = v4l2.V4L2_MEMORY_MMAP
		if fcntl.ioctl(self.camera, v4l2.VIDIOC_DQBUF, dqbuf):
			print 'Failed to get frame...index:%d' %dqbuf.index
			return False
		else:
			nparr = numpy.asarray(bytearray(self._mmaps[dqbuf.index]), numpy.uint8)
			if config.FormatPixelformat is v4l2.V4L2_PIX_FMT_YUYV:
				yuvarray = nparr.reshape((config.imageOperatingSize[1], config.imageOperatingSize[0], 2))
				img = cv2.cvtColor(yuvarray, cv2.COLOR_YUV2BGR_YUYV)
			else:
				img = cv2.imdecode(nparr, cv2.CV_LOAD_IMAGE_COLOR)

			self.currentFrame['content'] = img
			fcntl.ioctl(self.camera, v4l2.VIDIOC_QBUF, dqbuf)
			return True

    def _start_capture(self):
		buftype = v4l2.v4l2_buf_type(v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE)
		if fcntl.ioctl(self.camera, v4l2.VIDIOC_STREAMON, buftype):
			print 'Failed to start capture...'

    def _stop_capture(self):
		if fcntl.ioctl(self.camera, v4l2.VIDIOC_STREAMOFF, v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE):
			print 'Failed to stop capture...'

    def _release_buffers(self):
		for cnt in range (0, len(self._mmaps)):
			self._mmaps[cnt].close()
		self._mmaps = []
		self._buffers = []

    def _alloc_buffers(self):
		req = v4l2.v4l2_requestbuffers()
		req.count = config.V4l2ReqBuffersCount
		req.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		req.memory = v4l2.V4L2_MEMORY_MMAP
		if fcntl.ioctl(self.camera, v4l2.VIDIOC_REQBUFS, req):
			print 'Failed to request buffers...'
		
		self.bufferscount = req.count
		print 'request buffers:%d' %self.bufferscount

		self._buffers = []
		self._mmaps = []
		for cnt in range (0, req.count):
			buf = v4l2.v4l2_buffer()
			self._buffers.append(buf)
			buf.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
			buf.memory = v4l2.V4L2_MEMORY_MMAP
			buf.index = cnt
			if fcntl.ioctl(self.camera, v4l2.VIDIOC_QUERYBUF, buf):
				print 'failed to query buffers...'
			else:
				print 'index:%d, length:%d' %(buf.index, buf.length)

			self._mmaps.append(mmap.mmap(self.camera, buf.length, mmap.MAP_SHARED, mmap.PROT_READ|mmap.PROT_WRITE, offset = buf.m.offset))
			fcntl.ioctl(self.camera, v4l2.VIDIOC_QBUF, buf)

    def _set_device_controls(self):
        queryctrl = v4l2.v4l2_queryctrl()
        queryctrl.id = self.CtrlId
        if fcntl.ioctl(self.camera, v4l2.VIDIOC_QUERYCTRL, queryctrl):
            print 'queryctrl.id:0x%x is not supprotted' %(queryctrl.id)
        else:
            print 'queryctrl id:0x%x,type:%d,name:%s,minimum:%d,maximum:%d,step:%d\n' %(queryctrl.id, queryctrl.type, queryctrl.name,queryctrl.minimum, queryctrl.maximum, queryctrl.step)

        ctrl = v4l2.v4l2_control()
        ctrl.id = self.CtrlId
        if fcntl.ioctl(self.camera, v4l2.VIDIOC_G_CTRL, ctrl):
            print 'ctrl.id:0x%x is not supprotted' %(ctrl.id)
        else:
            print 'Get current control...id:0x%x,valus:%d\n' %(ctrl.id, ctrl.value)

        ctrl = v4l2.v4l2_control()
        ctrl.id = self.CtrlId
        ctrl.value = self.CtrlValue
        if fcntl.ioctl(self.camera, v4l2.VIDIOC_S_CTRL, ctrl):
            print 'ctrl.id:0x%x is not supprotted' %(ctrl.id)
        else:
            print 'Set control...id:0x%x,valus:%d\n' %(ctrl.id, ctrl.value)

        ctrl = v4l2.v4l2_control()
        ctrl.id = self.CtrlId
        if fcntl.ioctl(self.camera, v4l2.VIDIOC_G_CTRL, ctrl):
            print 'ctrl.id:0x%x is not supprotted' %(ctrl.id)
        else:
            print 'Check current control...id:0x%x,valus:%d\n' %(ctrl.id, ctrl.value)

    def _Configure_controls(self):

        self.CtrlId = v4l2.V4L2_CID_BRIGHTNESS
        self.CtrlValue = config.ControlBrightness
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_CONTRAST
        self.CtrlValue = config.ControlContrast
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_SATURATION
        self.CtrlValue = config.ControlSaturation
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_GAIN
        self.CtrlValue = config.ControlGain
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_AUTO_WHITE_BALANCE
        self.CtrlValue = config.ControlWhiteBalanceAuto
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_WHITE_BALANCE_TEMPERATURE
        self.CtrlValue = config.ControlWhiteBalanceTemperature
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_SHARPNESS
        self.CtrlValue = config.ControlSharpness
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_BACKLIGHT_COMPENSATION
        self.CtrlValue = config.ControlBacklightCompensation
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_EXPOSURE_AUTO
        self.CtrlValue = config.ControlExposureAuto
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_EXPOSURE_ABSOLUTE
        self.CtrlValue = config.ControlExposureAbsolute
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_FOCUS_AUTO
        self.CtrlValue = config.ControlFocusAuto
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_FOCUS_ABSOLUTE
        self.CtrlValue = config.ControlFocusAbsolute
        self._set_device_controls()

        self.CtrlId = v4l2.V4L2_CID_ZOOM_ABSOLUTE
        self.CtrlValue = config.ControlZoomAbsolute
        self._set_device_controls()

    def _configure_format(self):
		print 'Check format description ...'
		fmtdesc = v4l2.v4l2_fmtdesc()
		fmtdesc.index = 0
		fmtdesc.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		print 'Support format:'
		if not fcntl.ioctl(self.camera, v4l2.VIDIOC_ENUM_FMT, fmtdesc):
			print 'index:%d,type:%d,flags:%d,description:%s,pixelformat:%x\n' %(fmtdesc.index, fmtdesc.type,fmtdesc.flags, fmtdesc.description, fmtdesc.pixelformat)
			fmtdesc.index = fmtdesc.index + 1
		if not fcntl.ioctl(self.camera, v4l2.VIDIOC_ENUM_FMT, fmtdesc):
			print 'index:%d,type:%d,flags:%d,description:%s,pixelformat:%x\n' %(fmtdesc.index, fmtdesc.type,fmtdesc.flags, fmtdesc.description, fmtdesc.pixelformat)

		print 'Get current video format ...'
		video_format = v4l2.v4l2_format()
		video_format.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		if not fcntl.ioctl(self.camera, v4l2.VIDIOC_G_FMT, video_format):
			print 'type:%d,width:%d,height:%d,pixelformat:0x%x,field:%d\n' %(video_format.type, video_format.fmt.pix.width,video_format.fmt.pix.height, video_format.fmt.pix.pixelformat, video_format.fmt.pix.field)

		print 'Set current video format ...'
		video_format.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		video_format.fmt.pix.width = config.imageOperatingSize[0]
		video_format.fmt.pix.height = config.imageOperatingSize[1]
		video_format.fmt.pix.pixelformat = config.FormatPixelformat
		video_format.fmt.pix.field = config.FormatField

		if not fcntl.ioctl(self.camera, v4l2.VIDIOC_S_FMT, video_format):
			print 'Set format successfuly'

		print 'Check video format ...'
		video_format = v4l2.v4l2_format()
		video_format.type = v4l2.V4L2_BUF_TYPE_VIDEO_CAPTURE
		if not fcntl.ioctl(self.camera, v4l2.VIDIOC_G_FMT, video_format):
			print 'type:%d,width:%d,height:%d,pixelfformat:0x%x,field:%d\n' %(video_format.type, video_format.fmt.pix.width,video_format.fmt.pix.height, video_format.fmt.pix.pixelformat, video_format.fmt.pix.field)
		self.sizeimage = video_format.fmt.pix.sizeimage

    def _check_capabilities(self):
		cap = v4l2.v4l2_capability()
		fcntl.ioctl(self.camera, v4l2.VIDIOC_QUERYCAP, cap)
		print 'driver:%s,card:%s,bus_info:%s,capabilities:%x' %(cap.driver,cap.card,cap.bus_info,cap.capabilities)

    def _init_camera(self):
        self.camera = os.open(config.CameraDevice, os.O_RDWR, 0)
        print 'Device is opened', self.camera
        self._check_capabilities()
        self._configure_format()
        self._Configure_controls()
        self._alloc_buffers()

    def start(self):
        self.gameOn = True
        self._init_camera()
        self._start_capture()
        time.sleep(0.5)
        while self.gameOn:
            if self._handle_frame():
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
#                self.camera.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, self.posFrame - 1)
                cv2.waitKey(200)
            time.sleep(0.05)
        cv2.destroyAllWindows()
        self._stop_capture()
        self._release_buffers()
        os.close(config.V4l2Device)

    def stop(self):
        self.gameOn = False


