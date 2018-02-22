import yolo_server
import cv2

filename = './test.png'

img = cv2.imread(filename)
resized_img = cv2.resize(img, (960, 540))
res = yolo_server.predict(resized_img)

for k,v in enumerate(res):
	print k
	print v
