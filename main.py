import tkinter as tk
from ui_components import UIController

class WatermarkApp:
    # main tool
    def __init__(self):
        self.root = tk.Tk()
        self.root.config()
        self.root.title("Simple Image Watermarking Tool")
        self.ui_controller = UIController(self.root)

    def run(self):
        # initialise the tool
        self.root.mainloop()


if __name__ == "__main__":
    app = WatermarkApp()
    app.run()