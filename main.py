import tkinter as tk

from ui import OpsConsole


def main():
    root = tk.Tk()
    try:
        root.tk.call("wm", "class", root._w, "OpsConsole")
    except tk.TclError:
        pass
    OpsConsole(root)
    root.mainloop()


if __name__ == "__main__":
    main()
