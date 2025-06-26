from abc import ABC, abstractmethod

class ImageModifier(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def modify_image(self, img_obj, img_boxes_coordinates):
        pass