import cv2
from config import config

def _dist_of_two(box_a, box_b):
    x = box_a['left'] - box_b['left']
    y = box_a['top'] - box_b['top']
    return x**2 + y**2


def _get_bounding_box(boxes):
    x_list = []
    y_list = []
    for box in boxes:
        x_list.append(box['left'])
        y_list.append(box['top'])
    return {
        'x1': min(x_list),
        'x2': max(x_list),
        'y1': min(y_list),
        'y2': max(y_list),
        'width': max(x_list) - min(x_list),
        'height': max(y_list) - min(y_list)
    }


def _get_max_min_distance(centers):
    # logic: in initial state, the max of all min distance between each ball shoudld be small
    min_dists = []
    for centerA in centers:
        min_dist = 9999
        for centerB in centers:
            if centerB['class'] is not centerA['class']:
                dist = _dist_of_two(centerA, centerB)
                print 'dist is ', dist
                min_dist = min(min_dist, dist)
        print 'min_dist is', min_dist
        min_dists.append(min_dist)
    print 'min_dists:', min_dists
    return max(min_dists)


def is_initial_state(data):
    if len(data) == 0:
        return False
    boxes = []
    for ball in data:
        print 'ball is ', ball
        if ball['class'] is not '0':
            boxes.append(ball)
    if len(boxes) == 0:
	return False
    bounding_box = _get_bounding_box(boxes)
    # max_min_distance = _get_max_min_distance(boxes)
    print 'bounding box:', bounding_box
    # print 'max_min_distance:', max_min_distance
    # print 'bounding box width%d height%d: len(data):%d' %(bounding_box['width'], bounding_box['height'], len(data))

    if bounding_box['width'] < config.initial_bounding_box_limit and bounding_box['height'] < config.initial_bounding_box_limit:
        # if max_min_distance < 20:
        if(len(data)) > config.initial_ball_count_limit:
            return True
    return False
