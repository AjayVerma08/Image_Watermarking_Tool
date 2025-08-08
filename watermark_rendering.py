from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import os
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from data_manager import WatermarkSettings


class WatermarkRenderer(ABC):
    # watermark renderer base

    @abstractmethod
    def render(self, background_size: Tuple[int, int], settings: WatermarkSettings) -> Image.Image:
        # render the background for given background size
        pass


class TextWatermarkRenderer(WatermarkRenderer):
    # text based watermark renderer

    def render(self, background_size: Tuple[int, int], settings: WatermarkSettings) -> Image.Image:
        """Render text watermark"""
        text = settings.text or ""

        # Choose font
        font = self._get_font(settings.font_path, settings.font_size)

        # Measure text
        text_w, text_h = self._measure_text(text, font)
        if text_w == 0:
            text_w = text_h = 1

        # Create text image
        padding = 20
        txt_img = Image.new("RGBA", (text_w + padding * 2, text_h + padding * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_img)

        # Apply color and opacity
        r, g, b, a = settings.text_color
        a = int(a * (settings.opacity / 100.0))
        draw.text((padding, padding), text, font=font, fill=(r, g, b, a))

        # Scale and rotate
        txt_img = self._scale_image(txt_img, background_size, settings.size_percent, text_w, padding)
        if settings.rotation % 360 != 0:
            txt_img = self._rotate_image(txt_img, settings.rotation)

        return txt_img

    def _get_font(self, font_path: Optional[str], font_size: int) -> ImageFont.ImageFont:
        # gets the font
        try:
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size=font_size)
            else:
                return ImageFont.truetype("arial.ttf", size=font_size)
        except Exception:
            return ImageFont.load_default()

    def _measure_text(self, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        # measures the text dimensions
        tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tmp)

        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return draw.textsize(text, font=font)

    def _scale_image(self, img: Image.Image, bg_size: Tuple[int, int], size_percent: int,
                     text_w: int, padding: int) -> Image.Image:
        # scaling the image based on percentage
        bg_w, bg_h = bg_size
        target_w = max(1, int(bg_w * (size_percent / 100.0)))
        scale = target_w / float(text_w)
        new_w = max(1, int((text_w + padding * 2) * scale))
        new_h = max(1, int(img.height * scale))
        return img.resize((new_w, new_h), Image.LANCZOS)

    def _rotate_image(self, img: Image.Image, rotation: int) -> Image.Image:
        # rotating the image
        return img.rotate(rotation, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))


class ImageWatermarkRenderer(WatermarkRenderer):
    # rotating image watermarks

    def __init__(self):
        self.watermark_image: Optional[Image.Image] = None

    def set_watermark_image(self, image: Image.Image):
        # setting the watermark image
        self.watermark_image = image.convert("RGBA")

    def render(self, background_size: Tuple[int, int], settings: WatermarkSettings) -> Image.Image:
        # render image watermark
        if self.watermark_image is None:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        wm = self.watermark_image.copy()
        bg_w, bg_h = background_size

        # Scale watermark
        target_w = max(1, int(bg_w * (settings.size_percent / 100.0)))
        scale = target_w / float(wm.width)
        new_w = max(1, int(wm.width * scale))
        new_h = max(1, int(wm.height * scale))
        wm = wm.resize((new_w, new_h), Image.LANCZOS)

        # Apply opacity
        if settings.opacity < 100:
            alpha = wm.split()[3]
            alpha = ImageEnhance.Brightness(alpha).enhance(settings.opacity / 100.0)
            wm.putalpha(alpha)

        # Apply rotation
        if settings.rotation % 360 != 0:
            wm = wm.rotate(settings.rotation, expand=True, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))

        return wm


class WatermarkProcessor:
    # handle the watermark processing

    def __init__(self):
        self.text_renderer = TextWatermarkRenderer()
        self.image_renderer = ImageWatermarkRenderer()

    def create_watermark(self, background_size: Tuple[int, int], settings: WatermarkSettings) -> Image.Image:
        # creates the water based on the settings
        if settings.wm_type == "text":
            return self.text_renderer.render(background_size, settings)
        else:
            return self.image_renderer.render(background_size, settings)

    def create_overlay(self, original_size: Tuple[int, int], settings: WatermarkSettings) -> Image.Image:
        # overlay for final image
        orig_w, orig_h = original_size
        overlay = Image.new("RGBA", (orig_w, orig_h), (0, 0, 0, 0))

        # Create watermark at full resolution
        watermark = self.create_watermark(original_size, settings)

        # Position watermark
        cx = int(settings.anchor_ratio[0] * orig_w)
        cy = int(settings.anchor_ratio[1] * orig_h)
        top_left_x = int(cx - watermark.width / 2)
        top_left_y = int(cy - watermark.height / 2)

        overlay.paste(watermark, (top_left_x, top_left_y), watermark)
        return overlay

    def set_watermark_image(self, image: Image.Image):
        # passing the watermark image for renderer
        self.image_renderer.set_watermark_image(image)