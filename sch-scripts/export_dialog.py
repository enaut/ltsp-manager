#!/usr/bin/python

from gi.repository import Gtk
import libuser

class ExportDialog:
    def __init__(self, system, users):
        self.csv = libuser.CSV()
        chooser = Gtk.FileChooserDialog(title="Select a filename to export", 
                                        action=Gtk.FileChooserAction.SAVE,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        
        chooser.set_default_response(Gtk.ResponseType.OK)
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            self.csv.write(chooser.get_filename(), system, users)
        
        chooser.destroy()
