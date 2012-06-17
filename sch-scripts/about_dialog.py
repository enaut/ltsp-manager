#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>


from gi.repository import Gtk


class AboutDialog:
    def __init__(self):
        self.builder = Gtk.Builder()
        self.builder.add_from_file("about_dialog.ui")
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object("aboutdialog1")
        self.dialog.set_title("Περί Διαχείριση ΣΕΠΕΗΥ")
        self.dialog.run()
        self.dialog.destroy()
        
