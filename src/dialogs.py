# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

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
        

class ProgressDialog():
    def __init__(self, title, amount_of_operations, parent_widget, on_close=None):
        self.parent = parent_widget
        self.total = amount_of_operations

        self.glade = Gtk.Builder()
        self.glade.add_from_resource('/org/ltsp/ltsp-manager/ui/dialogs.ui')
        self.glade.connect_signals(self)

        self.progress_dialog = self.glade.get_object('progress_dialog')
        self.progress_dialog.set_transient_for(self.parent)
        self.progress_dialog.set_title(title)
        self.progress_dialog.set_modal(True)
        self.progress_dialog.show()
        self.progressbar = self.glade.get_object('users_progressbar')
        self.num = 1

        self.on_close = on_close

    def set_message(self, message):
        self.progressbar.set_text(message)

    def set_error(self, message):
        self.glade.get_object('error_label').set_text(message)
        self.glade.get_object('error_hbox').show()
        button_close = self.glade.get_object('button_close')
        button_close.set_sensitive(True)

    def set_progress(self, num):
        self.num = num
        self.progressbar.set_fraction(float(num) / float(self.total))
        if num == self.total:
            self.progressbar.set_text("done")
            self.glade.get_object('success_hbox').show()
            button_close = self.glade.get_object('button_close')
            button_close.set_sensitive(True)

    def inc(self):
        self.set_progress(self.num + 1)

    def on_progress_button_close_clicked(self, widget):
        if self.on_close and (self.num >= self.total):
            self.on_close()
        self.progress_dialog.destroy()

def wait_gtk():
    while Gtk.events_pending():
        Gtk.main_iteration()
