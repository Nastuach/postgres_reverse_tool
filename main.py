import tkinter as tk
from app import ModernPostgresReverseApp


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernPostgresReverseApp(root)
    root.mainloop()