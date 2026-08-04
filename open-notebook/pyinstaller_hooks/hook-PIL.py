# PyInstaller hook override for the desktop EXE build.
#
# The desktop app does not use Tk-based imaging widgets, so we keep Pillow
# from pulling in ImageTk/_imagingtk and the Tcl/Tk runtime.
excludedimports = ["tkinter", "PIL.ImageTk", "PIL._imagingtk"]
