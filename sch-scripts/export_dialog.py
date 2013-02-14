#!/usr/bin/python
#-*- coding: utf-8 -*-

import os
from gi.repository import Gtk
import parsers
import common

class ExportDialog:
    def __init__(self, system, users):
        self.csv = parsers.CSV()
        chooser = Gtk.FileChooserDialog(title="Επιλέξτε όνομα αρχείου για εξαγωγή", 
                                        action=Gtk.FileChooserAction.SAVE,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        chooser.set_icon_from_file('/usr/share/pixmaps/sch-scripts.svg') 
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_do_overwrite_confirmation(True)
        homepath = os.path.expanduser('~')
        chooser.set_current_folder(homepath)
        filename = 'users_%s_%s.csv' % (os.uname()[1], common.date())
        i = 1
        while os.path.isfile(os.path.join(homepath, filename)):
            filename = 'users_%s_%s.%d.csv' % (os.uname()[1], common.date(), i)
            i += 1
        chooser.set_current_name(filename)
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            if filename[-4:] != '.csv':
                filename += '.csv'
            self.csv.write(filename, system, users)
            os.chown(filename, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
        
        chooser.destroy()
