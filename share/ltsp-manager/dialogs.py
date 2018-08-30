import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class AskDialog(Gtk.MessageDialog):
    def __init__(self, message, title="", parent=None):
        super(AskDialog, self).__init__(type = Gtk.MessageType.WARNING,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.YES_NO,
                                          message_format = message)
        self.set_title(title)
        self.set_default_response(Gtk.ResponseType.NO)
        self.set_transient_for(parent)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response


class InfoDialog(Gtk.MessageDialog):
    def __init__(self, message, title="", parent=None):
        super(InfoDialog, self).__init__(type = Gtk.MessageType.INFO,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
        self.set_transient_for(parent)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response

class WarningDialog(Gtk.MessageDialog):
    def __init__(self, message, title="", parent=None):
        super(WarningDialog, self).__init__(type = Gtk.MessageType.WARNING,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
        self.set_transient_for(parent)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response

class ErrorDialog(Gtk.MessageDialog):
    def __init__(self, message, title="", parent=None):
        super(ErrorDialog, self).__init__(type = Gtk.MessageType.ERROR,
                                          flags = Gtk.DialogFlags.MODAL,
                                          buttons = Gtk.ButtonsType.CLOSE,
                                          message_format = message)
        self.set_title(title)
        self.set_transient_for(parent)
    
    def showup(self):
        response = self.run()
        self.destroy()
        return response
        

