# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import version


class AboutDialog:
    def __init__(self, main_window):
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/about_dialog.ui')
        self.dialog = self.builder.get_object("aboutdialog1")
        self.dialog.set_version(version.__version__)
        self.dialog.set_transient_for(main_window)
        self.dialog.run()
        self.dialog.destroy()
