# 2017, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import os
import parsers

import common

class ExportDialog:
    def __init__(self, main_window, system, users):
        self.csv = parsers.CSV()
        chooser = Gtk.FileChooserDialog(title=_("Enter the name for the exported file"), 
                                        action=Gtk.FileChooserAction.SAVE,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        chooser.set_icon_from_file('../pixmaps/ltsp-manager.svg')
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
        chooser.set_transient_for(main_window)
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            filename = chooser.get_filename()
            if filename[-4:] != '.csv':
                filename += '.csv'
            self.csv.write(filename, system, users)
            os.chown(filename, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
        
        chooser.destroy()
