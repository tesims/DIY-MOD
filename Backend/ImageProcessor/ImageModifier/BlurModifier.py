import cv2
from .ImageModifier import ImageModifier

class BlurModifier(ImageModifier):

    def __init__(self):
        super().__init__()

    def modify_image(self, img_obj, img_boxes_coordinates):
        for i in range(len(img_boxes_coordinates)):
            coordinate = img_boxes_coordinates[i]
            roi = img_obj[coordinate[1]:coordinate[3], coordinate[0]:coordinate[2]]
            # blurred_roi = cv2.GaussianBlur(roi, (105, 105), 200)
            blurred_roi = cv2.medianBlur(roi, 123)
            img_obj[coordinate[1]:coordinate[3], coordinate[0]:coordinate[2]] = blurred_roi
            # cv2.rectangle(img_cv_obj, (coordinate[0], coordinate[1]), (coordinate[2], coordinate[3]), (0, 255, 0), 2)
            # # Add a caption to the top-left of the rectangle
            # cv2.putText(img_cv_obj, 'Modified by DIY-MOD', (coordinate[0], coordinate[1] - 10), 
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        return img_obj