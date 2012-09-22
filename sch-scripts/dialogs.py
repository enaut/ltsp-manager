#!/usr/bin/python

from gi.repository import Gtk

class AskDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(AskDialog, self).__init__(type = Gtk.MessageType.WARNING,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.YES_NO,
                                          message_format = message)
        self.set_title(title)
        self.set_default_response(Gtk.ResponseType.NO)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response


class InfoDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(InfoDialog, self).__init__(type = Gtk.MessageType.INFO,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response

class WarningDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(WarningDialog, self).__init__(type = Gtk.MessageType.WARNING,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response

class ErrorDialog(Gtk.MessageDialog):
    def __init__(self, message, title=""):
        super(ErrorDialog, self).__init__(type = Gtk.MessageType.ERROR,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response
        

