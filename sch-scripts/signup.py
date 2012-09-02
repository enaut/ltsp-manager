#!/usr/bin/python
#-*- coding: utf-8 -*-
import socket
import os
import sys
import re
import crypt
import random
from gi.repository import Gtk

import common

class Connection:
    def __init__(self, host, port):
        # Create a new socket and connect to the server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        
        # 'Identify' to the server
        host = socket.gethostname()
        self._send('ID %s' % host)
        
        self.p_reg = None
        self.u_reg = None
        self.n_reg = None
    
    # TODO: Review the recv call, there should be a better way
    # TODO: Show exceptions in a graphical message
    def _send(self, data):
        if not data.endswith('\r\n'):
            data += '\r\n'
        self.sock.send(data)
        return self.sock.recv(4096).strip()
    
    def close(self):
        self._send("BYE")
        self.sock.close()
    
    def get_groups(self):
        groups = self._send("GET_GROUPS")
        if groups != '':
            return groups.split(',')
        return []
    
    def get_roles(self):
        roles = self._send("GET_ROLES")
        if roles != '':
            return roles.split(',')
        return []
    
    def user_exists(self, username):
        return self._send("USER_EXISTS %s" % username) == "YES"
    
    def realname_regex(self):
        if self.n_reg is None:
            self.n_reg = self._send("REALNAME_REGEX")
        return self.n_reg
    
    def username_regex(self):
        if self.u_reg is None:
            self.u_reg = self._send("USER_REGEX")
        return self.u_reg
    
    def password_regex(self):
        if self.p_reg is None:
            self.p_reg = self._send("PASS_REGEX")
        return self.p_reg
    
    def send_data(self, realname, username='', password='', role='', groups=''):
        groups = ','.join(groups)
        data = '\t'.join([realname, username, password, role, groups])
        return self._send("SEND_DATA %s" % data) == "YES"


class UserForm(object):
    def __init__(self, host='server', port=790):
        try:
            self.connection = Connection(host, port)
        except socket.error as e:
            msg1 = "Πιθανόν ο διαχειριστής να μην έχει ενεργοποιήσει τις εγγραφές."
            msg2 = "Πιθανόν να υπάρχει πρόβλημα δικτύου."
            msg = "Σφάλμα %d: %s\n\n%s" % (e.errno, e.strerror, msg1 if e.errno == 111 else msg2)
            dlg = Gtk.MessageDialog(type = Gtk.MessageType.ERROR,
                                    buttons = Gtk.ButtonsType.CLOSE,
                                    message_format = msg)
            dlg.set_title("Σφάλμα σύνδεσης")
            dlg.run()
            dlg.destroy()
            sys.exit(1)
        
        self.builder = Gtk.Builder()
        self.builder.add_from_file('signup_form.ui')  
        self.dialog = self.builder.get_object('dialog')
        self.username_combo = self.builder.get_object('username_combo')
        self.username_entry = self.username_combo.get_child()
        self.password = self.builder.get_object('password_entry')
        self.retype_password = self.builder.get_object('retype_password_entry')
        self.realname = self.builder.get_object('realname_entry')
        self.groups_box = self.builder.get_object('groups_box')
        self.groups_tree = self.builder.get_object('groups_tree')
        self.groups_store = self.builder.get_object('groups_store')
        self.role_combo = self.builder.get_object('role_combo')
        self.builder.connect_signals(self)
        #self.groups_store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        # Workaround the problem with starting with a sensitive button (but an empty model)
        self.username_combo.set_button_sensitivity(Gtk.SensitivityType.OFF)
        self.username_combo.set_button_sensitivity(Gtk.SensitivityType.AUTO)
        
        # Fill the groups treeview or hide it if there are no groups to select
        groups = self.connection.get_groups()
        
        if len(groups) > 0:
            for group in groups:
                self.groups_store.append([False, group])
        else:
            self.groups_box.hide()
        
        # Fill the roles combobox or hide it if there are no roles to select
        roles = self.connection.get_roles()
        if len(roles) > 0:
            for role in roles:
                self.role_combo.append_text(role)
            self.role_combo.set_active(0) # Select the first role by default
        else:
            self.role_combo.hide()
            self.builder.get_object('role_label').hide()
            
        self.dialog.show()
    
    def on_group_toggled(self, widget, path):
        self.groups_store[path][0] = not self.groups_store[path][0]
    
    def get_icon(self, check):
        if check:
            return Gtk.STOCK_OK
        return Gtk.STOCK_DIALOG_ERROR
    
    def to_alpha(self, s):
        return ''.join(c for c in s if c.isalpha())

    def get_suggestions(self, name):
        name = common.greek_to_latin(name)
        tokens = []
        for tok in name.split():
            t = self.to_alpha(tok).lower()
            if t:
                tokens.append(t)
        if len(tokens) == 0:
            return []
        sug = []
        _append = lambda x: sug.append(x) if x not in sug else False # FIXME? heh
        _append(tokens[0] + ''.join(tok[0] for tok in tokens[1:]))
        _append(''.join(tok[0] for tok in tokens[:-1]) + tokens[-1])
        _append(''.join(tok[0] for tok in tokens[1:]) + tokens[0])
        _append(tokens[-1] + ''.join(tok[0] for tok in tokens[:-1]))
        _append(tokens[-1])
        _append(tokens[0])
        
        return sug
    
    def on_realname_entry_changed(self, widget):
        name = widget.get_text()
        icon = self.get_icon(re.match(self.connection.realname_regex(), name.decode('utf-8'), re.UNICODE))
        self.username_combo.remove_all()
        sug = self.get_suggestions(name)
        sug = [s for s in sug if re.match(self.connection.username_regex(), s.decode('utf-8'), re.UNICODE) and not self.connection.user_exists(s)]
        if sug:
            self.username_entry.set_text(sug[0])
            for s in sug:
                self.username_combo.append_text(s)
        self.builder.get_object('realname_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_password_entry_changed(self, widget):
        password = widget.get_text()
        password_repeat = self.retype_password.get_text()
        icon = self.get_icon(password == password_repeat)
        self.builder.get_object('retype_password_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        
        icon = self.get_icon(re.match(self.connection.password_regex(), password.decode('utf-8'), re.UNICODE))
        self.builder.get_object('password_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_retype_password_entry_changed(self, widget):
        password = self.password.get_text()
        password_repeat = widget.get_text()
        icon = self.get_icon(password == password_repeat)
        self.builder.get_object('retype_password_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_username_entry_changed(self, widget):
        username = self.username_entry.get_text()
        valid_name = re.match(self.connection.username_regex(), username.decode('utf-8'), re.UNICODE)
        free_name = not self.connection.user_exists(username)
        icon = self.get_icon(valid_name and free_name)
        self.builder.get_object('username_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def set_apply_sensitivity(self):
        icon = lambda x: self.builder.get_object(x).get_stock()[0]
        s = icon('username_valid') == icon('password_valid') == icon('retype_password_valid') == icon('realname_valid') == Gtk.STOCK_OK
        
        self.builder.get_object('apply_button').set_sensitive(s)

    def on_dialog_delete_event(self, widget, event):
        self.quit()
    
    def on_cancel_clicked(self, widget):
        self.quit()
    
    def on_apply_clicked(self, widget):
        realname = self.realname.get_text()
        username = self.username_entry.get_text()
        password = self.encrypt(self.password.get_text())
        role = self.role_combo.get_active_text() or ''
        groups = [g[1] for g in self.groups_store if g[0]]
        if self.connection.send_data(realname, username, password, role, groups):
            msg = "Το αίτημά σας καταχωρήθηκε επιτυχώς για αναθεώρηση."
            dlg = Gtk.MessageDialog(parent = self.dialog,
                                    type = Gtk.MessageType.INFO,
                                    flags = Gtk.DialogFlags.MODAL,
                                    buttons = Gtk.ButtonsType.CLOSE,
                                    message_format = msg)
            dlg.set_title("Επιτυχία")
        else:
            msg = "Αποτυχία αποστολής του αιτήματός σας. Ζητήστε βοήθεια από τον υπεύθυνο."
            dlg = Gtk.MessageDialog(parent = self.dialog,
                                    type = Gtk.MessageType.ERROR,
                                    flags = Gtk.DialogFlags.MODAL,
                                    buttons = Gtk.ButtonsType.CLOSE,
                                    message_format = msg)
            dlg.set_title("Αποτυχία")
        
        self.connection.close()
        self.connection = None
        dlg.run()
        dlg.destroy()
        self.quit()
    
    def encrypt(self, pwd):
        alphabet = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        salt = ''.join([random.choice(alphabet) for i in range(8)])
        return crypt.crypt(pwd, "$6$%s$" % salt)
    
    def quit(self):
        self.dialog.destroy()
        if self.connection:
            self.connection.close()
        sys.exit()
    
if __name__ == '__main__':
    if len(sys.argv) > 2:
        form = UserForm(sys.argv[1], int(sys.argv[2]))
    elif len(sys.argv) > 1:
        form = UserForm(sys.argv[1])
    else:
        form = UserForm()
    Gtk.main()
