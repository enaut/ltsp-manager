# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

from gi.repository import Gtk


class GroupForm():
    def __init__(self, bus, account_manager, parent):
        self.parent = parent
        self.bus = bus
        self.account_manager = account_manager
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/group_form.ui')

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
        self.show_sys_users = False
        self.mode = "undefined"
        self.group = None

        self.dialog.set_transient_for(parent)

        self.users_filter.set_visible_func(self.users_visible_func)
        self.users_sort.set_sort_column_id(2, Gtk.SortType.ASCENDING)

    def populate_users(self):
        # Fill the users (member selection) treeview
        gid = self.group.GetGID()
        for user_path in self.account_manager.ListUsers():
            user_obj = self.bus.get_object('io.github.ltsp-manager', user_path)
            user_name = user_obj.GetUsername()
            # The users with this group as main GID can not be edited.
            if self.mode == 'edit' and user_obj.GetGID() == gid:
                activatable = False
            else:
                activatable = True
            self.users_store.append([user_obj, False, user_name, activatable])

    def on_show_sys_users_toggled(self, widget):
        self.show_sys_users = not self.show_sys_users
        self.users_filter.refilter()

    def users_visible_func(self, model, itr, _x):
        if self.show_sys_users:
            return True
        system_user = model[itr][0].IsSystemUser()
        return not system_user

    def on_name_entry_changed(self, widget):
        groupname = widget.get_text()

        if (self.mode == "edit" and groupname == self.group.GetGroupName()) or all(self.account_manager.IsGroupNameValidAndFree(groupname)):
            icon = Gtk.STOCK_OK
        else:
            icon = Gtk.STOCK_CANCEL
        self.gname_valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gid_changed(self, widget):
        """React to changes in the Group ID field. Validate if the ID is valid and free."""
        gid = widget.get_text()
        try:
            gid = int(gid)
        except ValueError:
            self.gid_valid_icon.set_from_stock(Gtk.STOCK_CANCEL, Gtk.IconSize.BUTTON)
            self.set_apply_sensitivity()
            return

        valid_and_free = self.account_manager.IsGIDValidAndFree(gid)
        if (self.mode == 'edit' and gid == self.group.GetGID()) or all(valid_and_free):
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
        sensitive = self.gid_valid_icon.get_stock()[0] == self.gname_valid_icon.get_stock()[0] == Gtk.STOCK_OK
        self.builder.get_object('apply_button').set_sensitive(sensitive)

    def on_dialog_delete_event(self, widget, event):
        self.dialog.destroy()

    def on_cancel_clicked(self, widget):
        self.dialog.destroy()


class NewGroupDialog(GroupForm):
    def __init__(self, bus, account_manager, parent):
        super().__init__(bus, account_manager, parent)
        self.mode = 'new'
        self.builder.connect_signals(self)
        self.populate_users()

        self.dialog.show()

    def on_apply_clicked(self, widget):
        name = self.groupname.get_text()
        members = [u[0] for u in self.users_store if u[1]]
        group_path = self.account_manager.CreateGroup(name)
        group = self.bus.get_object('io.github.ltsp-manager', group_path)
        for user in members:
            group.AddUser(user.object_path)
        self.dialog.destroy()


class EditGroupDialog(GroupForm):
    def __init__(self, group, bus, account_manager, parent):
        super(EditGroupDialog, self).__init__(bus, account_manager, parent)
        self.mode = 'edit'
        self.group = group
        self.builder.connect_signals(self)

        self.groupname.set_text(self.group.GetGroupName())
        self.gid_entry.set_text(str(self.group.GetGID()))

        self.populate_users()
        # Activate the members of the group
        for row in self.users_store:
            members = self.group.GetAllMembers()
            if row[0].object_path in members:
                row[1] = True
        self.on_gid_changed(self.gid_entry)
        self.on_name_entry_changed(self.groupname)
        self.dialog.show()

    def on_apply_clicked(self, widget):
        old_members = self.group.GetUsers()

        new_name = self.groupname.get_text()
        new_gid = int(self.gid_entry.get_text())
        new_members = [u[0] for u in self.users_store if u[1]]

        self.group.SetValues(new_gid, new_name)
        for user in new_members:
            if user.object_path not in old_members:
                self.group.AddUser(user.object_path)
        new_paths = [user.object_path for user in new_members]
        for user_path in old_members:
            if user_path not in new_paths:
                self.group.RemoveUser(user_path)

        self.dialog.destroy()
