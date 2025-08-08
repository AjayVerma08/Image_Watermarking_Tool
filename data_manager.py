from dataclasses import dataclass
from typing import Tuple, Optional
from PIL import Image, ImageTk

@dataclass
class WatermarkSettings:
    # holds watermark configuration
    wm_type: str = "text"
    text: str = "Sample Watermark"
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 200)
    font_path: Optional[str] = None
    font_size: int = 36
    size_percent: int = 20
    rotation: int = 0
    anchor_ratio: Tuple[float, float] = (0.5, 0.5)
    opacity: int = 50


class ImageManager:
    # handles the processing of the image

    def __init__(self, canvas_width: int = 900, canvas_height: int = 600):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[Image.Image] = None
        self.display_photo: Optional[ImageTk.PhotoImage] = None

    def load_image(self, path: str) -> bool:
        # load the file path for the image
        try:
            img = Image.open(path).convert("RGBA")
            self.original_image = img
            self._update_display_image()
            return True
        except Exception as e:
            print(f"Error loading image: {e}")
            return False

    def _update_display_image(self):
        # showing a scaled preview of the image
        if self.original_image is None:
            return

        img = self.original_image.copy()
        img.thumbnail((self.canvas_width, self.canvas_height), Image.LANCZOS)
        self.display_image = img
        self.display_photo = ImageTk.PhotoImage(self.display_image)

    def get_display_info(self) -> Tuple[int, int, int, int]:
        # gets the image position info
        if self.display_image is None:
            return 0, 0, 0, 0

        img_x = (self.canvas_width - self.display_image.width) // 2
        img_y = (self.canvas_height - self.display_image.height) // 2
        return img_x, img_y, self.display_image.width, self.display_image.height