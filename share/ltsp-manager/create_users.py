# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

import datetime
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import config
import libuser
import ltsp_shared_folders
import dialogs

class NewUsersDialog:
    def __init__(self, system, sf, parent):
        self.system = system
        self.parent = parent
        self.sf = sf

        self.glade = Gtk.Builder()
        self.glade.add_from_file('create_users.ui')
        self.glade.connect_signals(self)
        self.dialog = self.glade.get_object('create_users_dialog')
        self.dialog.set_transient_for(self.parent)
        self.user_tree = self.glade.get_object('user_treeview')
        self.user_store = self.glade.get_object('user_liststore')
        
        self.roles = {i : config.parser.get('roles', i) for i in config.parser.options('roles')}
        self.groups = []
        
        self.glade.get_object('computers_number_spin').set_value(12)
        for group in self.roles["student"].split(","):
            if group in self.system.groups:
                self.groups.append(group)   
        self.glade.get_object('groups_template_entry').set_text("{c} "+" ".join(self.groups))
        self.dialog.show()

        self.help_dialog = self.glade.get_object('help_dialog')

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
        
        # Check the validity of characters in the classes entry#FIXME: libuser
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
        
        # Check the validity of characters in the username entry #FIXME: libuser
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
        
        # Repopulate the store
        for classn in self.classes:
            for compn in range(1, self.computers+1):
                if len(self.user_store) == 300:
                    break
                ev = lambda x: x.replace('{c}', classn.strip()).replace('{i}', 
                    str(compn)).replace('{0i}', '%02d' %compn)
                self.user_store.append([ev(self.username_tmpl), ev(self.name_tmpl),
                    '/home/'+ev(self.username_tmpl),ev(self.password_tmpl)])

        users_number = self.computers * len(self.classes)
        self.glade.get_object('users_number_label').set_text(
            _("The following %d accounts will be created") % users_number)

    def on_button_apply_clicked(self, widget):
        self.computers = self.glade.get_object('computers_number_spin').\
            get_value_as_int()
        self.groups_tmpl = self.glade.get_object('groups_template_entry').\
            get_text()
        button_close = self.glade.get_object('button_close')

        total_users = self.computers * len(self.classes)
        total_groups = len(self.classes)

        progress = dialogs.ProgressDialog(_("Creating all users"), total_users + total_groups, self.dialog, on_close=self.on_button_cancel_clicked)

        users_created = 0
        groups_created = 0
        set_gids = []
        set_uids = []

        # Create groups for all the listed classes
        if self.classes != ['']:
            for classn in self.classes:
                dialogs.wait_gtk()
                if classn not in self.system.groups:
                    tmp_gid = self.system.get_free_gid(exclude=set_gids)
                    set_gids.append(tmp_gid)
                    cmd_error = self.system.add_group(libuser.Group(classn, tmp_gid, {}))
                    progress.set_message(_("Creating group %(current)d of %(total)d...")
                        % {"current":groups_created+1, "total":total_groups})
                    if cmd_error[0] and cmd_error[1] != "":
                        self.glade.get_object('error_label').set_text(cmd_error[1])
                        self.glade.get_object('error_hbox').show() 
                        button_close.set_sensitive(True)
                        return
                    groups_created += 1
                    progress.set_progress(groups_created)
                else:
                    tmp_gid=self.system.groups[classn].gid
                    groups_created += 1
                
                # Add teachers to group
                if self.glade.get_object('teachers_checkbutton').get_active():
                    progress.set_message(_("Adding teachers to group {group}").format(group=classn))
                    for user in self.system.users.values():
                        dialogs.wait_gtk()
                        if 'teachers' in user.groups and classn not in user.groups:
                            user.groups.append(classn)
                            self.system.update_user(user.name, user)
            
            # Create shared folders
            if self.glade.get_object('shared_checkbutton').get_active():
                for classn in self.classes:
                    progress.set_message(_("Adding shares for {group}").format(group=classn))
                    dialogs.wait_gtk()
                    self.sf.add([classn])
                

        # And finally, create the users
        cmd_error = (False, '')
        for classn in self.classes:
            for compn in range(1, self.computers+1):
                dialogs.wait_gtk()
                progress.set_message(_("Creating user %(current)d of %(total)d...")
                    % {"current":users_created+1, "total":total_users})

                ev = lambda x: x.replace('{c}', classn.strip()).replace('{i}', 
                                str(compn)).replace('{0i}', '%02d'%compn)
                epoch = datetime.datetime.utcfromtimestamp(0)
                uname = ev(self.username_tmpl)
                tmp_uid = self.system.get_free_uid(exclude=set_uids)
                set_uids.append(tmp_uid)
                tmp_gid = self.system.get_free_gid(exclude=set_gids)
                tmp_password=ev(self.password_tmpl)
                # Create the UPG
                g = libuser.Group(uname, tmp_gid)
                self.system.add_group(g)
                u=libuser.User(name=uname, uid=tmp_uid,
                    gid=tmp_gid, rname=ev(self.name_tmpl),
                    directory=('/home/'+ev(self.username_tmpl)),
                    lstchg = (datetime.datetime.today() - epoch).days,
                    groups=[classn],
                    password=self.system.encrypt(tmp_password))
                cmd_error = self.system.add_user(u)
                self.system.load()
                users_created += 1
                progress.set_progress(groups_created + users_created)

        if cmd_error[0] and cmd_error[1] != "":
            self.progress.set_error(cmd_error.strip())
            return

    def on_button_cancel_clicked(self, widget=None):
        self.dialog.destroy()
        self.help_dialog.destroy()

    def on_button_help_clicked(self, widget):
        self.help_dialog.show()

    def on_help_close_clicked(self, widget, dummy=None):
        self.help_dialog.hide()
        return True

