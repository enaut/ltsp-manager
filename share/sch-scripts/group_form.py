#!/usr/bin/python
#-*- coding: utf-8 -*-

import re
import os
import subprocess
from gi.repository import Gtk, Gdk
import libuser
import shared_folders

class GroupForm(object):
    def __init__(self, system, sf, refresh):
        self.system = system
        self.sf = sf
        #self.mode = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file('group_form.ui')
        
        self.refresh = refresh #OMG FIXME
        
        self.dialog = self.builder.get_object('dialog')
        self.groupname = self.builder.get_object('name_entry')
        self.gid_entry = self.builder.get_object('gid_entry')
        self.users_tree = self.builder.get_object('users_treeview')
        self.users_store = self.builder.get_object('users_liststore')
        self.users_filter = self.builder.get_object('users_filter')
        self.users_sort = self.builder.get_object('users_sort')
        self.sys_group_check = self.builder.get_object('sys_group_check')
        self.gname_valid_icon = self.builder.get_object('groupname_valid')
        self.gid_valid_icon = self.builder.get_object('gid_valid')
        self.has_shared = self.builder.get_object('shared_folders_check')
        self.show_sys_users = False
        
        self.users_filter.set_visible_func(self.users_visible_func)
        self.users_sort.set_sort_column_id(2, Gtk.SortType.ASCENDING)
        
        # Fill the users (member selection) treeview
        for user, user_obj in system.users.iteritems():
            if self.mode == 'edit' and user_obj.gid == self.group.gid:
                activatable = False
            else:
                activatable = True
            self.users_store.append([user_obj, False, user, activatable])
    
    def on_show_sys_users_toggled(self, widget):
        self.show_sys_users = not self.show_sys_users
        self.users_filter.refilter()
    
    def users_visible_func(self, model, itr, x):
        system_user = model[itr][0].is_system_user()
        return self.show_sys_users or not system_user
    
    def on_name_entry_changed(self, widget):
        groupname = widget.get_text()
        valid_name = self.system.name_is_valid(groupname)
        free_name = groupname not in self.system.groups
        if self.mode == 'edit':
            free_name = free_name or groupname == self.group.name
        
        if valid_name and free_name:
            icon = Gtk.STOCK_OK
        else:
            icon = Gtk.STOCK_CANCEL
        self.gname_valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_gid_changed(self, widget):
        gid = widget.get_text()
        try:
            gid = int(gid)
        except:
            self.gid_valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            self.set_apply_sensitivity()
            return
        
        if (self.mode == 'edit' and gid == self.group.gid) or self.system.gid_is_free(gid):
            icon = Gtk.STOCK_OK
        else:
            icon = Gtk.STOCK_CANCEL
        self.gid_valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()
    
    def on_user_toggled(self, widget, path):
        path = self.users_sort[path].path
        path = self.users_sort.convert_path_to_child_path(path)
        path = self.users_filter.convert_path_to_child_path(path)
        
        self.users_store[path][1] = not self.users_store[path][1]
    
    def set_apply_sensitivity(self):
        s = self.gid_valid_icon.get_stock()[0] == self.gname_valid_icon.get_stock()[0] == Gtk.STOCK_OK
        self.builder.get_object('apply_button').set_sensitive(s)
    
    def on_dialog_delete_event(self, widget, event):
        self.dialog.destroy()
    
    def on_cancel_clicked(self, widget):
        self.dialog.destroy()
    
class NewGroupDialog(GroupForm):
    def __init__(self, system, sf, refresh):
        self.mode = 'new'
        super(NewGroupDialog, self).__init__(system, sf, refresh)
        self.builder.connect_signals(self)
        
        self.gid_entry.set_text(str(system.get_free_gid()))
        
        self.dialog.show()
    
    def on_apply_clicked(self, widget):
        name = self.groupname.get_text()
        gid = int(self.gid_entry.get_text())
        members = {u[0].name : u[0] for u in self.users_store if u[1]}
        g = libuser.Group(name, gid, members)
        self.system.add_group(g)
        self.refresh()
        if self.has_shared.get_active():
            self.sf.add([g.name])
        self.dialog.destroy()

class EditGroupDialog(GroupForm):
    def __init__(self, system, sf, group, refresh):
        self.mode = 'edit'
        self.group = group
        super(EditGroupDialog, self).__init__(system, sf, refresh)
        self.builder.connect_signals(self)
        
        self.groupname.set_text(group.name)
        self.gid_entry.set_text(str(group.gid))
        
        # Activate the members of the group
        for row in self.users_store:
            if row[0].name in self.group.members:
                row[1] = True
        
        # See if the group has shared folders enabled
        if group.name in self.sf.list_shared():
            self.has_shared.set_active(True)
            self.shared_state = True
        else:
            self.shared_state = False
        
        self.has_shared.connect('toggled', self.on_has_shared_check_toggled)
        
        self.dialog.show()
    
    def on_has_shared_check_toggled(self, widget):
        warn_label = self.builder.get_object('warning')
        if not self.has_shared.get_active() and self.shared_state:
            warn_label.show()
        else:
            warn_label.hide()
    
    def on_apply_clicked(self, widget):
        old_name = self.group.name
        old_gid = self.group.gid
        old_members = self.group.members
        self.group.name = self.groupname.get_text()
        self.group.gid = int(self.gid_entry.get_text())
        self.group.members = {u[0].name : u[0] for u in self.users_store if u[1]}
        
        self.system.edit_group(old_name, self.group)
        
        # Remove the group from users that are no more members of this group
        for user in old_members.values():
            if user not in self.group.members.values():
                self.system.remove_user_from_groups(user, [self.group])
        if self.shared_state and not self.has_shared.get_active():
            # Shared folders were active but now they are not
            self.sf.remove([self.group.name])
        elif self.has_shared.get_active():
            if not self.shared_state:
                # Shared folders were not active and now they are
                self.sf.add([self.group.name])
            else:
                # Share folders were and are active, check for name/gid changes
                if old_name != self.group.name:
                    self.sf.rename(old_name, self.group.name)
                elif old_gid != self.group.gid:
                    self.sf.mount([self.group.name])

        self.refresh()
        self.dialog.destroy()
