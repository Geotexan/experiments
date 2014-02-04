#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 You <your.email@someplace>

"""Base template"""


from gi.repository import Gtk as gtk
from lib import graphics

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()
