#!/usr/bin/python
#-*- coding: utf-8 -*-

from gi.repository import Gtk, Gdk
import libuser

class GroupForm(object):
    def __init__(self, system, refresh):
        self.system = system
        #self.mode = None
        self.builder = Gtk.Builder()
        self.builder.add_from_file('group_form.ui')
        
        self.refresh = refresh #OMG FIXME
        
        self.dialog = self.builder.get_object('dialog')
        self.groupname = self.builder.get_object('name_entry')
        self.gid_entry = self.builder.get_object('gid_entry')
        self.users_tree = self.builder.get_object('users_treeview')
        self.users_store = self.builder.get_object('users_liststore')
        self.sys_group_check = self.builder.get_object('sys_group_check')
        self.gname_valid_icon = self.builder.get_object('groupname_valid')
        self.gid_valid_icon = self.builder.get_object('gid_valid')
        
        # Fill the users (member selection) treeview
        for user, user_obj in system.users.iteritems():
            if self.mode == 'edit' and user_obj.gid == self.group.gid:
                activatable = False
            else:
                activatable = True
            self.users_store.append([user_obj, False, user, activatable])
        
    def on_name_entry_changed(self, widget):
        groupname = widget.get_text()
        valid_name = self.system.is_valid_name(groupname)
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
        self.users_store[path][1] = not self.users_store[path][1]
    
    def set_apply_sensitivity(self):
        s = self.gid_valid_icon.get_stock()[0] == self.gname_valid_icon.get_stock()[0] == Gtk.STOCK_OK
        self.builder.get_object('apply_button').set_sensitive(s)
    
    def on_dialog_delete_event(self, widget, event):
        self.dialog.destroy()
    
    def on_cancel_clicked(self, widget):
        self.dialog.destroy()
    
class NewGroupDialog(GroupForm):
    def __init__(self, system, refresh):
        self.mode = 'new'
        super(NewGroupDialog, self).__init__(system, refresh)
        self.builder.connect_signals(self)
        
        self.gid_entry.set_text(str(system.get_free_gid()))
        
        self.dialog.show_all()
    
    def on_apply_clicked(self, widget):
        name = self.groupname.get_text()
        gid = int(self.gid_entry.get_text())
        members = {u[0].name : u[0] for u in self.users_store if u[1]}
        self.system.add_group(libuser.Group(name, gid, members))
        self.refresh()
        self.dialog.destroy()

class EditGroupDialog(GroupForm):
    def __init__(self, system, group, refresh):
        self.mode = 'edit'
        self.group = group
        super(EditGroupDialog, self).__init__(system, refresh)
        self.builder.connect_signals(self)
        
        self.groupname.set_text(group.name)
        self.gid_entry.set_text(str(group.gid))
        
        # Activate the members of the group
        for row in self.users_store:
            if row[0].name in self.group.members:
                row[1] = True
            
        self.dialog.show_all()
    
    def on_apply_clicked(self, widget):
        name = self.group.name
        self.group.name = self.groupname.get_text()
        self.group.gid = int(self.gid_entry.get_text())
        old_members = self.group.members
        self.group.members = {u[0].name : u[0] for u in self.users_store if u[1]}
        self.system.edit_group(name, self.group)
        for user in old_members.values():
            if user not in self.group.members.values():
                self.system.remove_user_from_groups(user, [self.group])
        self.refresh()
        self.dialog.destroy()
