#!/usr/bin/python
#-*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

from gi.repository import Gtk
import libuser
import config


class NewUsersDialog:
    def __init__(self, system, refresh):
        self.system = system
        self.refresh = refresh
        self.glade = Gtk.Builder()
        self.glade.add_from_file('create_users.ui')
        self.glade.connect_signals(self)
        self.dialog = self.glade.get_object('create_users_dialog')
        self.user_tree = self.glade.get_object('user_treeview')
        # uname, name, pass respectively
        self.user_store = Gtk.ListStore(str, str, str)

        self.user_tree.set_model(self.user_store)

        # Create the columns for self.user_tree
        names = ['Όνομα χρήστη', 'Πραγματικό όνομα', 'Κωδικός πρόσβασης']
        for i in range(3):
            column = Gtk.TreeViewColumn(names[i], Gtk.CellRendererText(),
                                        text=i)
            column.set_resizable(True)
            column.set_reorderable(True)
            column.set_sort_column_id(i)
            self.user_tree.append_column(column)

        self.user_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.glade.get_object('computers_number_spin').set_value(12)
        self.roles = {i : config.parser.get('Roles', i) for i in config.parser.options('Roles')}
        
        text = "{c}"
        
        text = " ".join(self.roles['Μαθητής'].split(","))
        self.groups_tmpl = self.glade.get_object('groups_template_entry').set_text("{c} "+text)

        
        self.dialog.show()

    def on_template_changed(self, widget=None):
        classes_str = self.glade.get_object('classes_entry').get_text().strip()
        self.classes = classes_str.split()
        self.computers = self.glade.get_object('computers_number_spin').\
            get_value_as_int()
        self.username_tmpl = self.glade.get_object('username_template_entry').\
            get_text()
        self.name_tmpl = self.glade.get_object('name_template_entry').\
            get_text()
        self.password_tmpl = self.glade.get_object('password_template_entry').\
            get_text()

        button_apply = self.glade.get_object('button_apply')
        
        # Check the validity of characters in the classes entry
        classes_validity_image = self.glade.get_object('classes_validity_image')
        if not (classes_str.replace(' ', '') + 'foo').isalnum():
            classes_validity_image.set_from_stock(Gtk.STOCK_DIALOG_ERROR, 
                                        Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(False)
            return
        else:
            if self.classes == []:
                self.classes = ['']
            classes_validity_image.set_from_stock(Gtk.STOCK_OK, 
                                            Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(True)
        
        # Check the validity of characters in the username entry
        username_validity_image = self.glade.get_object(
            'username_validity_image')
        if (not self.username_tmpl.replace('{c}', 'a').replace('{0i}', 
          'a').replace('{i}', 'a').replace('-', '').replace('_', '').isalnum()) or \
          (len(self.classes) == 1 and self.computers > 1 and not '{i}' in self.username_tmpl and \
          not '{0i}' in self.username_tmpl) or (self.computers == 1 and len(self.classes) > 1 and \
          not '{c}' in self.username_tmpl) or (self.computers > 1 and len(self.classes) > 1 and \
          (not '{c}' in self.username_tmpl or (not '{0i}' in self.username_tmpl and \
          not '{i}' in self.username_tmpl))):

            username_validity_image.set_from_stock(Gtk.STOCK_DIALOG_ERROR, 
                                        Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(False)
            return
        else:
            username_validity_image.set_from_stock(Gtk.STOCK_OK, 
                                            Gtk.IconSize.SMALL_TOOLBAR)
            button_apply.set_sensitive(True)
        self.user_store.clear()

        for classn in self.classes:
            for compn in range(1, self.computers+1):
                if len(self.user_store) == 300:
                    break
                ev = lambda x: x.replace('{c}', classn.strip()).replace('{i}', 
                    str(compn)).replace('{0i}', '%02d' %compn)
                self.user_store.append([ev(self.username_tmpl), 
                    ev(self.name_tmpl), ev(self.password_tmpl)])

        users_number = self.computers * len(self.classes)
        self.glade.get_object('users_number_label').set_text(
            'Θα δημιουργηθούν οι παρακάτω %d λογαριασμοί' %users_number)

    def on_button_apply_clicked(self, widget):
        self.computers = self.glade.get_object('computers_number_spin').\
            get_value_as_int()
        self.groups_tmpl = self.glade.get_object('groups_template_entry').\
            get_text()
        button_close = self.glade.get_object('button_close')

        progress_dialog = self.glade.get_object('progress_dialog')
        progress_dialog.set_transient_for(self.dialog)
        progress_dialog.show()
        progressbar = self.glade.get_object('users_progressbar')
        total_users = self.computers * len(self.classes)
        total_groups = len(self.classes)
        users_created = 0
        groups_created = 0
        while Gtk.events_pending():
            Gtk.main_iteration()

        # Create groups for all the listed classes
        print self.classes
        if self.classes != ['']:
            for classn in self.classes:
                while Gtk.events_pending():
                    Gtk.main_iteration()
                print classn
                gid = self.system.get_free_gid()
                cmd_error = self.system.add_group(libuser.Group(classn, gid, {}))
                print cmd_error
                progressbar.set_text('Δημιουργία ομάδας %d από %d' 
                    % (groups_created+1, total_groups))
                if False and cmd_error != "":
                    self.glade.get_object('error_label').set_text(
                        cmd_error)
                    self.glade.get_object('error_hbox').show() 
                    button_close.set_sensitive(True)
                    return
                progressbar.set_fraction(
                    float(groups_created) / float(total_groups))

        # And finally, create the users
        cmd_error = str()
        for classn in self.classes:
            for compn in range(1, self.computers+1):
                while Gtk.events_pending():
                    Gtk.main_iteration()
                progressbar.set_text('Δημιουργία χρήστη %d από %d...' 
                    %(users_created+1, total_users))

                ev = lambda x: x.replace('{c}', classn.strip()).replace('{i}', 
                                str(compn)).replace('{0i}', '%02d'%compn)
                u=libuser.User(name=ev(self.username_tmpl), uid=str(self.system.get_free_uid()),
                    gid=gid, rname=ev(self.name_tmpl), directory=("/home/"+ev(self.username_tmpl)),
                    plainpw=ev(self.password_tmpl), groups=ev(self.groups_tmpl).split())
                print u.name, u.rname, u.plainpw, u.directory, u.groups
                self.system.add_user(u)
                users_created += 1
                progressbar.set_fraction(
                    float(users_created) / float(total_users))

        if False and cmd_error != "":
            self.glade.get_object('error_label').set_text(cmd_error.
                strip())
            self.glade.get_object('error_hbox').show()
            button_close.set_sensitive(True)
            return

        # Display a success message and make the Close button sensitive
        self.glade.get_object('success_hbox').show()
        button_close.set_sensitive(True)

    def on_progress_button_close_clicked(self, widget):
        self.dialog.destroy()

    def on_button_cancel_clicked(self, widget):
        self.dialog.destroy()

    def on_button_help_clicked(self, widget):
        dialog = self.glade.get_object('help_dialog')
        dialog.set_transient_for(self.dialog)
        dialog.run()
        dialog.hide()

