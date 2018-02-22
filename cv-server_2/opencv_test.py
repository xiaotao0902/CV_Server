import numpy as np
import cv2

#cap = cv2.VideoCapture('/home/ubuntu/Desktop/cv-server/1.mov')
cap = cv2.VideoCapture(0)

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()
    if ret:
	    # Our operations on the frame come here
    	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

	# Display the resulting frame
    	cv2.imshow('frame',gray)
    	if cv2.waitKey(1) & 0xFF == ord('q'):
        	break
    else:
	print 'Camera not ready'

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
