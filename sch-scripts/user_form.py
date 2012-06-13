#!/usr/bin/python
#-*- coding: utf-8 -*-

from gi.repository import Gtk, Gdk
import dialogs
import os
import libuser
import config

class UserForm(object):
    def __init__(self, system, refresh):
        self.system = system
        self.mode = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file('user_form.ui')
        self.roles = {i : config.parser.get('Roles', i) for i in config.parser.options('Roles')}
        self.refresh = refresh #OMG FIXME
        
        self.dialog = self.builder.get_object('dialog')
        self.username = self.builder.get_object('username_entry')
        self.password = self.builder.get_object('password_entry')
        self.password_repeat = self.builder.get_object('password_repeat_entry')
        self.uid_entry = self.builder.get_object('uid_entry')
        self.homedir = self.builder.get_object('homedir_entry')
        self.shells_combo = self.builder.get_object('shell_combo')
        self.shells_entry = self.builder.get_object('shell_combo_entry')
        self.gc_name = self.builder.get_object('gcos_name_entry')
        self.gc_office = self.builder.get_object('gcos_office_entry')
        self.gc_office_phone = self.builder.get_object('gcos_office_phone_entry')
        self.gc_home_phone = self.builder.get_object('gcos_home_phone_entry')
        self.gc_other = self.builder.get_object('gcos_other_entry')
        self.groups_tree = self.builder.get_object('groups_treeview')
        self.groups_store = self.builder.get_object('groups_liststore')
        self.last_change = self.builder.get_object('last_change')
        self.minimum = self.builder.get_object('minimum')
        self.maximum = self.builder.get_object('maximum')
        self.warn = self.builder.get_object('warn')
        self.inactive = self.builder.get_object('inactive_spin')
        self.expire = self.builder.get_object('expire')
        self.pgroup = self.builder.get_object('pgroup_entry')
        self.pgid = self.builder.get_object('pgid_entry')
        self.role_combo = self.builder.get_object('role_combo')
        self.primary_group = None
        self.active_from_role = []
        
        # Fill the groups treeview
        for group, group_obj in system.groups.iteritems():
            self.groups_store.append([group_obj, group, False, True, 400, False])
            
        # Fill the shells combobox
        for shell in system.get_valid_shells():
            self.shells_combo.append_text(shell)
            
        # Fill the roles combobox
        for role, groups in self.roles.iteritems():
            self.role_combo.append_text(role)
    
    def on_role_combo_changed(self, widget):
        role = widget.get_active_text()
        for row in self.active_from_role:
            row[2] = False
        self.active_from_role = []   
        
        if role is not None:
            groups = self.roles[role].split(',')
            for row in self.groups_store:
                if row[0].name in groups:
                    row[2] = True
                    self.active_from_role.append(row)
                    
    
    def on_uid_changed(self, widget):
        uid = widget.get_text()
        uid_valid_icon = self.builder.get_object('uid_valid')
        try:
            uid = int(uid)
        except:
            uid_valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            self.set_apply_sensitivity()
            return
        
        if (self.mode == 'edit' and uid == self.user.uid) or self.system.uid_is_free(uid):
            icon = Gtk.STOCK_OK
        else:
            icon = Gtk.STOCK_CANCEL
        uid_valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.on_homedir_entry_changed(self.homedir)
        self.set_apply_sensitivity()
    
    def on_group_toggled(self, widget, path):
        self.groups_store[path][2] = not self.groups_store[path][2]
        self.groups_store[path][5] = not self.groups_store[path][5]
        
        # Set a role if available
        # FIXME
        active_groups = [r[0].name for r in self.groups_store if r[2]]
        idx = None
        n = -1
        for role, groups in self.roles.iteritems():
            n += 1
            groups = groups.split(',')
            i = 0
            for g in groups:
                print g, g in active_groups
                if g in active_groups:
                    i += 1
            if i == len(groups):
                idx = n
                print idx
                break
        
        if idx is not None:
            self.role_combo.set_active(idx)
            
        
    def on_groups_selection_changed(self, widget):
        self.builder.get_object('set_primary_button').set_sensitive(len(widget.get_selected_rows()[1]) == 1)
    
    def on_set_primary_button_clicked(self, widget):
        # The paths list will always contain 1 element, I just use
        # get_selected_rows here instead of get_selected for extra features
        # such as context menu actions which would work with multiple selection
        model, paths = self.groups_tree.get_selection().get_selected_rows()
        
        row = model[paths[0]]
        
        # Mark the group as primary
        self.set_group_primary(row)
        
        # Set the primary group name and gid entries
        self.pgroup.set_text(row[0].name)
        self.pgid.set_text(str(row[0].gid))
    
    def unset_primary(self):
        if self.primary_group:
            self.primary_group[2] = self.primary_group[5]
            self.primary_group[3] = True
            self.primary_group[4] = 400
            self.primary_group = None
    
    def set_group_primary(self, row):
        # Unset the previous primary group
        self.unset_primary()
        row[2] = True # Activate this group
        row[3] = False # Make it non-(de)activatable since it's now primary
        row[4] = 700 # Make the name bold to distinguish it
        
        # Remember the new primary group
        self.primary_group = row
    
    def on_gcos_other_entry_changed(self, widget):
        icon = self.get_icon(self.system.is_valid_gecos(widget.get_text()))
        self.builder.get_object('other_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_home_phone_entry_changed(self, widget):
        icon = self.get_icon(self.system.is_valid_gecos(widget.get_text()))
        self.builder.get_object('home_phone_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_office_phone_entry_changed(self, widget):
        icon = self.get_icon(self.system.is_valid_gecos(widget.get_text()))
        self.builder.get_object('office_phone_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_office_entry_changed(self, widget):
        icon = self.get_icon(self.system.is_valid_gecos(widget.get_text()))
        self.builder.get_object('office_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_name_entry_changed(self, widget):
        icon = self.get_icon(self.system.is_valid_gecos(widget.get_text()))
        self.builder.get_object('full_name_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_password_repeat_entry_changed(self, widget):
        icon = self.get_icon(self.password_repeat.get_text() == self.password.get_text())
        self.builder.get_object('password_retype_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_password_entry_changed(self, widget):
        icon = self.get_icon(self.password_repeat.get_text() == self.password.get_text())
        self.builder.get_object('password_retype_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        
        icon = self.get_icon(self.password.get_text() != '')
        self.builder.get_object('password_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_username_entry_changed(self, widget):
        username = self.username.get_text()
        valid_name = self.system.is_valid_name(username)
        free_name = username not in self.system.users
        if self.mode == 'edit':
            free_name = free_name or username == self.user.name
        else:
            self.pgroup.set_text(username)
        self.homedir.set_text(os.path.join(libuser.HOME_PREFIX, username))
        icon = self.get_icon(valid_name and free_name)
        self.builder.get_object('username_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_homedir_entry_changed(self, widget):
        home = widget.get_text()
        try:
            gid = int(self.pgid.get_text())
        except:
            gid = None
        try:
            uid = int(self.uid_entry.get_text())
        except:
            uid = None
        valid_icon = self.builder.get_object('homedir_valid')
        valid_icon.set_tooltip_text("")
        valid_icon.set_from_stock(Gtk.STOCK_OK, Gtk.IconSize.BUTTON)
        if os.path.isdir(home):
            path_uid = os.stat(home).st_uid
            path_gid = os.stat(home).st_gid
            if path_uid != uid or path_gid != gid:
                if self.mode == 'new' or self.user.directory != home:
                    valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
                    valid_icon.set_tooltip_text("This directory belongs to UID %d and GID %d" % (path_uid, path_gid))
        else:
            if self.mode == 'edit' and self.user.directory != home:
                valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            else:
                valid_icon.set_from_stock(Gtk.STOCK_OK, Gtk.IconSize.BUTTON)
        
        self.set_apply_sensitivity()
    
    def on_pgroup_entry_changed(self, widget):
        pgname = self.pgroup.get_text()
        exists = pgname in self.system.groups
        icon = self.get_icon(self.system.is_valid_name(pgname))
        self.builder.get_object('pgroup_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        if exists:
            for row in self.groups_store:
                if row[0].name == pgname:
                    # Mark the group as primary in the tree
                    self.set_group_primary(row)
                    self.pgid.set_text(str(row[0].gid))
                    break
        else:
            self.unset_primary()
            try:
                gid = int(self.pgid.get_text())
            except:
                gid = None
            
            if gid is not None and not self.system.gid_is_free(gid):
                self.pgid.set_text(str(self.system.get_free_gid()))
        self.set_apply_sensitivity()
    
    def on_pgid_entry_changed(self, widget):
        valid_icon = self.builder.get_object('pgid_valid')
        try:
            gid = int(self.pgid.get_text())
        except:
            valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            if self.pgroup.get_text() in self.system.groups:
                self.pgroup.set_text('')
            self.set_apply_sensitivity()
            return
        
        exists = not self.system.gid_is_free(gid)
        icon = self.get_icon(self.system.gid_is_valid(gid))
        valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        if exists:
            for row in self.groups_store:
                if row[0].gid == gid:
                    # Mark the group as primary in the tree
                    self.set_group_primary(row)
                    self.pgroup.set_text(row[0].name)
                    break
        else:
            self.unset_primary()
            username = self.username.get_text()
            if self.pgroup.get_text() in self.system.groups:
                if self.system.is_valid_name(username) and username not in self.system.groups:
                    self.pgroup.set_text(username)
                else:
                    self.pgroup.set_text('')
        self.on_homedir_entry_changed(self.homedir)
        self.set_apply_sensitivity()
    
    def get_icon(self, check):
        if check:
            return Gtk.STOCK_OK
        return Gtk.STOCK_CANCEL
    
    def set_apply_sensitivity(self):
        icon = lambda x: self.builder.get_object(x).get_stock()[0]
        s = icon('username_valid') == icon('uid_valid') == icon('password_valid') == icon('password_retype_valid') == icon('full_name_valid') == icon('office_valid') == icon('office_phone_valid') == icon('home_phone_valid') == icon('other_valid') == icon('homedir_valid') == icon('pgid_valid') == icon('pgroup_valid') == Gtk.STOCK_OK
        
        self.builder.get_object('apply_button').set_sensitive(s)

    def on_dialog_delete_event(self, widget, event):
        self.dialog.destroy()
    
    def on_cancel_clicked(self, widget):
        self.dialog.destroy()
         
class NewUserDialog(UserForm):
    def __init__(self, system, refresh):
        super(NewUserDialog, self).__init__(system, refresh)
        self.mode = 'new'
        self.builder.connect_signals(self)
        
        # Set some defaults
        self.uid_entry.set_text(str(self.system.get_free_uid()))
        self.pgid.set_text(str(self.system.get_free_gid()))
        self.shells_entry.set_text('/bin/bash')
        
        self.dialog.show()
    
    def on_apply_clicked(self, widget):
        user = libuser.User()
        user.name = self.username.get_text()
        user.rname = self.gc_name.get_text()
        user.uid = int(self.uid_entry.get_text())
        user.office = self.gc_office.get_text()
        user.wphone = self.gc_office_phone.get_text()
        user.hphone = self.gc_home_phone.get_text()
        user.other = self.gc_other.get_text()
        user.directory = self.homedir.get_text()
        user.shell = self.shells_entry.get_text()
        user.lstchg = int(self.last_change.get_value())
        user.min = int(self.minimum.get_value())
        user.max = int(self.maximum.get_value())
        user.warn = int(self.warn.get_value())
        user.inact = int(self.inactive.get_value())
        user.expire = int(self.expire.get_value())
        user.password = self.system.encrypt(self.password.get_text())
        
        user.groups = [g[0].name for g in self.groups_store if g[2]]
        user.gid = int(self.pgid.get_text())
        if self.system.gid_is_free(user.gid):
            self.system.add_group(libuser.Group(self.pgroup.get_text(), user.gid, {}))
        
        self.system.add_user(user)
        self.refresh()
        self.dialog.destroy()
    
class EditUserDialog(UserForm):
    def __init__(self, system, user, refresh):
        super(EditUserDialog, self).__init__(system, refresh)
        self.mode = 'edit'
        self.user = user
        self.builder.connect_signals(self)
        
        self.builder.get_object('primary_group_grid').set_visible(False)
        
        self.username.set_text(user.name)
        self.password.set_text(u'\u03db\xa9\u03df-\u03db\xa9\xaei\u03e1\u03c4\u03db')
        self.password_repeat.set_text(u'\u03db\xa9\u03df-\u03db\xa9\xaei\u03e1\u03c4\u03db')
        self.uid_entry.set_text(str(user.uid))
        self.homedir.set_text(user.directory)
        self.shells_entry.set_text(user.shell)
        self.gc_name.set_text(user.rname)
        self.gc_office.set_text(user.office)
        self.gc_office_phone.set_text(user.wphone)
        self.gc_home_phone.set_text(user.hphone)
        self.gc_other.set_text(user.other)
        self.last_change.set_value(self.user.lstchg)
        self.minimum.set_value(self.user.min)
        self.maximum.set_value(self.user.max)
        self.warn.set_value(self.user.warn)
        self.inactive.set_value(self.user.inact)
        self.expire.set_value(self.user.expire)
        self.builder.get_object('locked_account_check').set_active(self.system.user_is_locked(self.user))
        
        self.pgroup.set_text(self.user.primary_group)
        # Activate the groups in which the user belongs and mark the primary
        for row in self.groups_store:
            if user.name in row[0].members:
                row[2] = True
                row[5] = True
            if row[1] == user.primary_group:
                self.primary_group = row
                self.set_group_primary(row)
        
        self.dialog.show()
        
    def on_apply_clicked(self, widget):
        username = self.user.name
        self.user.name = self.username.get_text()
        self.user.rname = self.gc_name.get_text()
        self.user.uid = int(self.uid_entry.get_text())
        self.user.office = self.gc_office.get_text()
        self.user.wphone = self.gc_office_phone.get_text()
        self.user.hphone = self.gc_home_phone.get_text()
        self.user.other = self.gc_other.get_text()
        self.user.directory = self.homedir.get_text()
        self.user.shell = self.shells_entry.get_text()
        self.user.lstchg = int(self.last_change.get_value())
        self.user.min = int(self.minimum.get_value())
        self.user.max = int(self.maximum.get_value())
        self.user.warn = int(self.warn.get_value())
        self.user.inact = int(self.inactive.get_value())
        self.user.expire = int(self.expire.get_value())
        if self.user.password == u'\u03db\xa9\u03df-\u03db\xa9\xaei\u03e1\u03c4\u03db':
            self.user.password = self.system.encrypt(self.password.get_text())
        
        self.user.groups = [g[1] for g in self.groups_store if g[2]]
        self.user.gid = self.primary_group[0].gid
        
        self.system.update_user(username, self.user)
        if self.builder.get_object('locked_account_check').get_active():
            self.system.lock_user(self.user)
        self.refresh()
        self.dialog.destroy()
