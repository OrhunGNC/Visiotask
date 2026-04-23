import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from src.gui.app import MacroApp

def main():
    root = tk.Tk()
    MacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
