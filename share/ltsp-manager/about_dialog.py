# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>
# 2017, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import version

class AboutDialog:
    def __init__(self, main_window):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("about_dialog.ui")
        self.dialog = self.builder.get_object("aboutdialog1")
        self.dialog.set_version(version.__version__)
        self.dialog.set_transient_for(main_window)
        self.dialog.run()
        self.dialog.destroy()
