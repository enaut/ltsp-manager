#!/usr/bin/python
#-*- coding: utf-8 -*-

import os
from gi.repository import Gtk
import libuser

class ExportDialog:
    def __init__(self, system, users):
        self.csv = libuser.CSV()
        chooser = Gtk.FileChooserDialog(title="Επιλέξτε όνομα αρχείου για εξαγωγή", 
                                        action=Gtk.FileChooserAction.SAVE,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_current_folder(os.path.expanduser('~'))
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            if filename[-4:] != '.csv':
                filename += '.csv'
            self.csv.write(filename, system, users)
            os.chown(filename, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
        
        chooser.destroy()
