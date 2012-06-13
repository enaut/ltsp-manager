#!/usr/bin/python

from gi.repository import Gtk

class AskDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(AskDialog, self).__init__(type = Gtk.MessageType.WARNING,
                                         flags = Gtk.DialogFlags.MODAL,
                                         buttons = Gtk.ButtonsType.YES_NO,
                                         message_format = message)
        self.set_title(title)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response

