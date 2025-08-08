import tkinter as tk
from tkinter import filedialog, colorchooser, ttk, messagebox
from PIL import Image, ImageTk
from typing import Tuple, Optional
from data_manager import WatermarkSettings, ImageManager
from watermark_rendering import WatermarkProcessor

class CanvasController:
    # Control the canvas display

    def __init__(self, canvas: tk.Canvas, image_manager: ImageManager):
        self.canvas = canvas
        self.image_manager = image_manager
        self.bg_image_id: Optional[int] = None
        self.watermark_id: Optional[int] = None
        self.watermark_photo: Optional[ImageTk.PhotoImage] = None
        self._drag_data = {"x": 0, "y": 0}

        # Callbacks
        self.on_position_change = None

    def update_background(self):
        # updates the background of canvas
        if self.image_manager.display_photo is None:
            return

        # Clear canvas
        self.canvas.delete("all")

        # Draw background image
        img_x, img_y, img_w, img_h = self.image_manager.get_display_info()
        self.bg_image_id = self.canvas.create_image(
            img_x, img_y, image=self.image_manager.display_photo,
            anchor="nw", tags=("bg",)
        )

    def update_watermark(self, watermark_img: Image.Image, settings: WatermarkSettings):
        # update the watermark on canvas
        if self.image_manager.display_image is None:
            return

        self.watermark_photo = ImageTk.PhotoImage(watermark_img)

        # Calculate position
        img_x, img_y, img_w, img_h = self.image_manager.get_display_info()
        cx = img_x + int(settings.anchor_ratio[0] * img_w)
        cy = img_y + int(settings.anchor_ratio[1] * img_h)

        # Update or create watermark
        if self.watermark_id is None:
            self.watermark_id = self.canvas.create_image(
                cx, cy, image=self.watermark_photo, anchor="center", tags=("watermark",)
            )
            self._bind_drag_events()
        else:
            self.canvas.coords(self.watermark_id, cx, cy)
            self.canvas.itemconfig(self.watermark_id, image=self.watermark_photo)

    def _bind_drag_events(self):
        # bind drag to canvas
        self.canvas.tag_bind("watermark", "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind("watermark", "<B1-Motion>", self._on_motion)
        self.canvas.tag_bind("watermark", "<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        # drag start
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.canvas.config(cursor="fleur")

    def _on_motion(self, event):
        # handle the drag motion
        if self.watermark_id is None:
            return

        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

        self.canvas.move(self.watermark_id, dx, dy)

        # Update anchor ratio
        if self.on_position_change:
            cx, cy = self.canvas.coords(self.watermark_id)
            img_x, img_y, img_w, img_h = self.image_manager.get_display_info()
            local_x = max(0, min(cx - img_x, img_w))
            local_y = max(0, min(cy - img_y, img_h))
            new_ratio = (local_x / float(img_w), local_y / float(img_h))
            self.on_position_change(new_ratio)

    def _on_release(self, event):
        # drag end
        self.canvas.config(cursor="")


class UIController:
    # controls the UI

    def __init__(self, root: tk.Tk):
        self.root = root
        self.settings = WatermarkSettings()

        # Initialize components
        self.image_manager = ImageManager()
        self.watermark_processor = WatermarkProcessor()

        # UI Variables
        self._init_variables()

        # Build UI
        self._build_ui()

        # Initialize canvas controller
        self.canvas_controller = CanvasController(self.canvas, self.image_manager)
        self.canvas_controller.on_position_change = self._on_position_drag

        # Initialize UI state
        self._update_ui_visibility()

    def _init_variables(self):
        # tkinter variables
        self.wm_type_var = tk.StringVar(value=self.settings.wm_type)
        self.font_size_var = tk.IntVar(value=self.settings.font_size)
        self.opacity_var = tk.IntVar(value=self.settings.opacity)
        self.size_var = tk.IntVar(value=self.settings.size_percent)
        self.rotation_var = tk.IntVar(value=self.settings.rotation)
        self.pos_var = tk.StringVar(value="center")

    def _build_ui(self):
        # generate the UI
        # Main frames
        control_frame = ttk.Frame(self.root)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)

        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Control widgets
        self._build_controls(control_frame)

        # Canvas
        self.canvas = tk.Canvas(canvas_frame, width=900, height=600, bg="#333333")
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def _build_controls(self, parent):
        # control widgets
        # Load image button
        ttk.Button(parent, text="Open Image", command=self._load_image).pack(fill=tk.X, pady=4)

        # Watermark type
        ttk.Label(parent, text="Watermark Type:").pack(anchor=tk.W, pady=(8, 8))
        type_combo = ttk.Combobox(parent, textvariable=self.wm_type_var, state="readonly",
                                  values=["text", "image"])
        type_combo.pack(fill=tk.X)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self._on_type_change())

        # Text controls frame
        self.text_frame = ttk.Frame(parent)
        self._build_text_controls(self.text_frame)

        # Image controls frame
        self.image_frame = ttk.Frame(parent)
        self._build_image_controls(self.image_frame)

        # Common controls
        self._build_common_controls(parent)

        # Save button
        ttk.Button(parent, text="Save Watermarked Image", command=self._save_image).pack(fill=tk.X, pady=12)

        # Help text
        ttk.Label(parent, text="Tip: Drag the watermark to fine-tune position.").pack(anchor=tk.W, pady=(12, 0))

    def _build_text_controls(self, parent):
        # text controls
        ttk.Label(parent, text="Watermark Text:").pack(anchor=tk.W)
        self.text_entry = ttk.Entry(parent)
        self.text_entry.insert(0, self.settings.text)
        self.text_entry.pack(fill=tk.X)
        self.text_entry.bind("<KeyRelease>", lambda e: self._update_settings())

        ttk.Button(parent, text="Choose Font File (.ttf)", command=self._choose_font).pack(fill=tk.X, pady=4)
        ttk.Button(parent, text="Choose Color", command=self._choose_color).pack(fill=tk.X, pady=4)

        ttk.Label(parent, text="Font size (px):").pack(anchor=tk.W)
        font_spin = ttk.Spinbox(parent, from_=6, to=300, textvariable=self.font_size_var, width=6,
                                command=self._update_settings)
        font_spin.pack(fill=tk.X)

    def _build_image_controls(self, parent):
        # image controls
        ttk.Button(parent, text="Open Watermark Image (PNG)",
                   command=self._choose_watermark_image).pack(fill=tk.X, pady=6)

    def _build_common_controls(self, parent):
        # common controls
        # Opacity
        ttk.Label(parent, text="Opacity (%):").pack(anchor=tk.W, pady=(8, 0))
        opacity_scale = ttk.Scale(parent, from_=0, to=100, variable=self.opacity_var,
                                  command=lambda e: self._update_settings())
        opacity_scale.pack(fill=tk.X)

        # Size
        ttk.Label(parent, text="Watermark width (% of image):").pack(anchor=tk.W, pady=(8, 0))
        size_scale = ttk.Scale(parent, from_=5, to=90, variable=self.size_var,
                               command=lambda e: self._update_settings())
        size_scale.pack(fill=tk.X)

        # Rotation
        ttk.Label(parent, text="Rotation (degrees):").pack(anchor=tk.W, pady=(8, 0))
        rot_scale = ttk.Scale(parent, from_=0, to=360, variable=self.rotation_var,
                              command=lambda e: self._update_settings())
        rot_scale.pack(fill=tk.X)

        # Position presets
        ttk.Label(parent, text="Position:").pack(anchor=tk.W, pady=(8, 0))
        pos_combo = ttk.Combobox(parent, textvariable=self.pos_var, state="readonly",
                                 values=["top-left", "top-center", "top-right",
                                         "center-left", "center", "center-right",
                                         "bottom-left", "bottom-center", "bottom-right", "custom"])
        pos_combo.pack(fill=tk.X)
        pos_combo.bind("<<ComboboxSelected>>", lambda e: self._on_position_preset())

    def _update_ui_visibility(self):
        # updating the UI
        if self.settings.wm_type == "text":
            self.text_frame.pack(fill=tk.X, pady=(8, 0))
            self.image_frame.pack_forget()
        else:
            self.text_frame.pack_forget()
            self.image_frame.pack(fill=tk.X, pady=(8, 0))

    def _update_settings(self):
        # watermark preview
        try:
            self.settings.text = self.text_entry.get()
            self.settings.font_size = int(self.font_size_var.get())
            self.settings.size_percent = int(self.size_var.get())
            self.settings.rotation = int(self.rotation_var.get())
            self.settings.opacity = int(self.opacity_var.get())
        except Exception:
            pass

        self._update_watermark_preview()

    def _update_watermark_preview(self):
        """Update watermark preview"""
        if self.image_manager.display_image is None:
            return

        watermark = self.watermark_processor.create_watermark(
            self.image_manager.display_image.size, self.settings
        )
        self.canvas_controller.update_watermark(watermark, self.settings)

    def _load_image(self):
        # Loading the BG Image
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.tif")])
        if not path:
            return

        if self.image_manager.load_image(path):
            self.settings.anchor_ratio = (0.5, 0.5)  # Reset position
            self.canvas_controller.update_background()
            self._update_watermark_preview()
        else:
            messagebox.showerror("Error", "Could not open image")

    def _on_type_change(self):
        # watermark type change
        self.settings.wm_type = self.wm_type_var.get()
        self._update_ui_visibility()
        self._update_watermark_preview()

    def _on_position_preset(self):
        # position selection
        preset = self.pos_var.get()
        mapping = {
            "top-left": (0.08, 0.08), "top-center": (0.5, 0.08), "top-right": (0.92, 0.08),
            "center-left": (0.08, 0.5), "center": (0.5, 0.5), "center-right": (0.92, 0.5),
            "bottom-left": (0.08, 0.92), "bottom-center": (0.5, 0.92), "bottom-right": (0.92, 0.92),
        }

        if preset in mapping:
            self.settings.anchor_ratio = mapping[preset]
            self._update_watermark_preview()

    def _on_position_drag(self, new_ratio: Tuple[float, float]):
        # position change on drag
        self.settings.anchor_ratio = new_ratio
        self.pos_var.set("custom")

    def _choose_font(self):
        # choose font file
        path = filedialog.askopenfilename(filetypes=[("Font files", "*.ttf;*.otf")])
        if path:
            self.settings.font_path = path
            self._update_watermark_preview()

    def _choose_color(self):
        # choose text color
        result = colorchooser.askcolor()
        if result and result[0]:
            r, g, b = [int(v) for v in result[0]]
            alpha = self.settings.text_color[3]
            self.settings.text_color = (r, g, b, alpha)
            self._update_watermark_preview()

    def _choose_watermark_image(self):
        # choose watermark image
        path = filedialog.askopenfilename(filetypes=[("PNG images", "*.png")])
        if not path:
            return

        try:
            wm_img = Image.open(path).convert("RGBA")
            self.watermark_processor.set_watermark_image(wm_img)
            self._update_watermark_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Could not open watermark image: {e}")

    def _save_image(self):
        # save watermarked image
        if self.image_manager.original_image is None:
            messagebox.showerror("Error", "Open a background image first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg;*.jpeg")]
        )
        if not path:
            return

        try:
            # Create overlay at full resolution
            overlay = self.watermark_processor.create_overlay(
                self.image_manager.original_image.size, self.settings
            )

            # Composite images
            base = self.image_manager.original_image.copy().convert("RGBA")
            result = Image.alpha_composite(base, overlay)

            # Save
            if path.lower().endswith((".jpg", ".jpeg")):
                result.convert("RGB").save(path, quality=95)
            else:
                result.save(path)

            messagebox.showinfo("Saved", f"Saved watermarked image to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save image: {e}")