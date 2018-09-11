# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

"""
Show the output of ltsp-info in a dialog.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import re
import textwrap

import common

class LtspInfo:
    def __init__(self, main_window):
        gladefile = "ltsp_info.ui"
        self.builder = Gtk.Builder()
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)
        self.dialog = self.builder.get_object("dialog1")
        self.dialog.set_transient_for(main_window)
        self.buffer = self.builder.get_object("textbuffer1")
        self.Fill()

    def Close(self, widget):
        self.dialog.destroy()

    def Fill(self):
        success, response = common.run_command(['ltsp-info', '-v'])
        self.buffer.set_text(response)
        self.dialog.show()
