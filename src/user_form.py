# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

"""
New user form.
"""
from gettext import gettext as _
import os
from gi.repository import Gtk
import common
import config
import paths


class UserForm():
    def __init__(self, bus, account_manager, parent):
        self.bus = bus
        self.account_manager = account_manager
        self.user = None
        self.mode = None
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/user_form19.ui')

        self.roles = {i: config.get_config().parser.get('roles', i).replace('$$teachers', 'teachers') for i in config.get_config().parser.options('roles')}
        self.selected_role = None

        self.dialog = self.builder.get_object('dialog')
        self.dialog.set_transient_for(parent)
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
        self.groups_filter = self.builder.get_object('groups_filter')
        self.groups_sort = self.builder.get_object('groups_sort')
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
        self.show_sys_groups = False
        self.active_from_role = []

        self.groups_filter.set_visible_func(self.groups_visible_func)
        self.groups_sort.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        # Fill the groups treeview
        # object, name, active, activatable, font weight, actually active, gid
        for grouppath in self.account_manager.ListGroups():
            group = self.bus.get_object('io.github.ltsp-manager', grouppath)
            self.groups_store.append([group, group.GetGroupName(), False, True, 400, False, group.GetGID()])

        # Fill the shells combobox
        for shell in self.get_valid_shells():
            self.shells_combo.append_text(shell)

        # Fill the roles combobox
        for role, _groups in self.roles.items():
            self.role_combo.append_text(role)

    # """ User Information """
    def on_username_entry_changed(self, widget):
        """ Update the home entry after a username change """
        username = self.username.get_text()
        valid_name, free_name = self.account_manager.IsUsernameValidAndFree(username)
        if self.mode == 'edit':
            valid = (valid_name and free_name) or username == self.user.GetUsername()
        else:
            valid = (valid_name and free_name)
        self.homedir.set_text(os.path.join(config.get_config().parser.get('users', 'home_base_directory'), username))
        icon = self.get_icon(valid)
        self.builder.get_object('username_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_password_entry_changed(self, widget):
        icon = self.get_icon(self.password.get_text() != '')
        self.builder.get_object('password_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_name_entry_changed(self, widget):
        icon = self.get_icon(self.gecos_is_valid(widget.get_text()))
        self.builder.get_object('full_name_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    # """ User Details """
    def on_uid_changed(self, widget):
        """ validate the UID. Check if it is either the current one, or it is in user range and free. """
        uid = widget.get_text()
        uid_valid_icon = self.builder.get_object('uid_valid')
        if not uid:
            uid_valid_icon.set_from_stock(self.get_icon(True), Gtk.IconSize.BUTTON)
            return
        try:
            uid = int(uid)
        except ValueError:
            uid_valid_icon.set_from_stock(self.get_icon(False), Gtk.IconSize.BUTTON)
            self.set_apply_sensitivity()
            return
        # Valid if either edit mode and own uid or the uid is free and in range of non system users.
        editvalid = (self.mode == 'edit' and uid == self.user.GetUID())
        valid = editvalid or all(self.account_manager.IsUIDValidAndFree(uid))

        icon = self.get_icon(valid)
        uid_valid_icon.set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.on_homedir_entry_changed(self.homedir)
        self.set_apply_sensitivity()

    def on_homedir_entry_changed(self, widget):
        """ validate the home directory permissions. """
        # TODO better validation
        home = widget.get_text()

        valid_icon = self.builder.get_object('homedir_valid')
        if not home:
            valid_icon.set_tooltip_text("")
            valid_icon.set_from_stock(self.get_icon(True), Gtk.IconSize.BUTTON)
            return
        try:
            gid = int(self.pgid.get_text())
        except ValueError:
            gid = None
        try:
            uid = int(self.uid_entry.get_text())
        except ValueError:
            uid = None
        valid_icon.set_tooltip_text("")
        valid_icon.set_from_stock(self.get_icon(True), Gtk.IconSize.BUTTON)
        if os.path.isdir(home):
            path_uid = os.stat(home).st_uid
            path_gid = os.stat(home).st_gid
            if path_uid != uid or path_gid != gid:
                if self.mode == 'new' or self.user.GetHomeDir() != home:
                    valid_icon.set_from_stock(self.get_icon(False), Gtk.IconSize.BUTTON)
                    tooltip_text = _("This directory belongs to UID %(uid)d and to GID %(gid)d") % {"uid": path_uid, "gid": path_gid}
                    valid_icon.set_tooltip_text(tooltip_text)
        else:
            if self.mode == 'edit' and self.user.GetHomeDir() != home:
                valid_icon.set_from_stock(self.get_icon(False), Gtk.IconSize.BUTTON)
            else:
                valid_icon.set_from_stock(self.get_icon(True), Gtk.IconSize.BUTTON)

        self.set_apply_sensitivity()

    @staticmethod
    def get_valid_shells():
        """ Get the shells from the file /etc/shells """
        try:
            fil = open(os.path.join(paths.sysconfdir, "shells"))
            shells = [line.strip() for line in fil.readlines() if line.strip()[0] != '#']
            fil.close()
        except:
            shells = []

        return shells

    def gecos_is_valid(self, field):
        return ':' not in field and ',' not in field

    def on_gcos_office_entry_changed(self, widget):
        icon = self.get_icon(self.gecos_is_valid(widget.get_text()))
        self.builder.get_object('office_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_office_phone_entry_changed(self, widget):
        icon = self.get_icon(self.gecos_is_valid(widget.get_text()))
        self.builder.get_object('office_phone_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_home_phone_entry_changed(self, widget):
        icon = self.get_icon(self.gecos_is_valid(widget.get_text()))
        self.builder.get_object('home_phone_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    def on_gcos_other_entry_changed(self, widget):
        icon = self.get_icon(self.gecos_is_valid(widget.get_text()))
        self.builder.get_object('other_valid').set_from_stock(icon, Gtk.IconSize.BUTTON)
        self.set_apply_sensitivity()

    """ Password Details """
    # No checks or setup

    """ Group memberships """

    def groups_visible_func(self, model, itr, x):
        row = model[itr]
        activatable = row[3]
        group = row[0]
        primary_group = not activatable or group.UsersAreMember(self.username.get_text())
        show_user_group = self.show_sys_groups or not group.IsSystemGroup()
        show_private_group = config.get_config().parser.getboolean('GUI', 'show_private_groups') or not model[itr][0].IsPrivateGroup()
        return (show_user_group and show_private_group) or primary_group

    def on_show_sys_groups_toggled(self, widget):
        self.show_sys_groups = not self.show_sys_groups
        self.groups_filter.refilter()
        if self.show_sys_groups:
            self.groups_sort.set_sort_column_id(6, Gtk.SortType.ASCENDING)
        else:
            self.groups_sort.set_sort_column_id(1, Gtk.SortType.ASCENDING)

    def on_role_combo_changed(self, widget):
        role = widget.get_active_text()
        self.selected_role = role
        for row in self.active_from_role:
            row[2] = False
        self.active_from_role = []

        if role is not None:
            groups = self.roles[role].split(',')
            for row in self.groups_store:
                if row[0].name in groups:
                    row[2] = True
                    self.active_from_role.append(row)

    def on_group_toggled(self, widget, path):
        path = self.groups_sort[path].path
        path = self.groups_sort.convert_path_to_child_path(path)
        path = self.groups_filter.convert_path_to_child_path(path)

        self.groups_store[path][2] = not self.groups_store[path][2]
        self.groups_store[path][5] = not self.groups_store[path][5]

    def on_groups_selection_changed(self, widget):
        """ Make the assign_primary_group_button sensitive if exactly one group is selected as main group"""
        self.builder.get_object('set_primary_button').set_sensitive(len(widget.get_selected_rows()[1]) == 1)

    def on_set_primary_button_clicked(self, widget):
        # The pathlist will always contain 1 element, I just use
        # get_selected_rows here instead of get_selected for extra features
        # such as context menu actions which would work with multiple selection
        _model, pathlist = self.groups_tree.get_selection().get_selected_rows()

        path = self.groups_sort[pathlist[0]].path
        path = self.groups_sort.convert_path_to_child_path(path)
        path = self.groups_filter.convert_path_to_child_path(path)
        row = self.groups_store[path]

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
        row[2] = True    # Activate this group
        row[3] = False   # Make it non-(de)activatable since it's now primary
        row[4] = 700     # Make the name bold to distinguish it

        # Remember the new primary group
        self.primary_group = row

    def on_pgroup_entry_changed(self, widget):
        pgname = self.pgroup.get_text()
        exists = self.account_manager.FindGroupByName(pgname) != "/None"
        icon = self.get_icon(self.account_manager.IsGroupNameValidAndFree(pgname))
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

            if gid is not None and not self.account_manager.IsGIDValidAndFree(gid):
                self.pgid.set_text('')
        self.set_apply_sensitivity()

    def on_pgid_entry_changed(self, widget):
        valid_icon = self.builder.get_object('pgid_valid')
        try:
            gid = int(self.pgid.get_text())
        except:
            valid_icon.set_from_stock(Gtk.STOCK_YES, Gtk.IconSize.BUTTON)
            # if self.pgroup.get_text() in self.system.groups:
            #    self.pgroup.set_text('')
            self.set_apply_sensitivity()
            return

        exists = not self.account_manager.IsGIDValidAndFree(gid)
        icon = self.get_icon(self.account_manager.IsGIDValidAndFree(gid))
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
            # if self.account_manager.FindGroupByName(pgroup.get_text()):
            #    if self.system.name_is_valid(username) and username not in self.system.groups:
            #        self.pgroup.set_text(username)
            #    else:
            #        self.pgroup.set_text('')
        self.on_homedir_entry_changed(self.homedir)
        self.set_apply_sensitivity()

    # """ General Methods """
    @staticmethod
    def get_icon(check):
        """Return the icon according to the boolean."""
        if check:
            return Gtk.STOCK_YES
        return Gtk.STOCK_NO

    def set_apply_sensitivity(self):
        """ Set the apply button sensitive when all values entered are ok. """
        def icon(x):
            return self.builder.get_object(x).get_stock()[0]

        ids = ['username_valid', 'uid_valid', 'password_valid', 'full_name_valid',
               'office_valid', 'office_phone_valid', 'home_phone_valid', 'other_valid',
               'homedir_valid', 'pgid_valid', 'pgroup_valid']
        sensitive = all([icon(x) == self.get_icon(True) for x in ids])
        self.builder.get_object('apply_button').set_sensitive(sensitive)

    def on_dialog_delete_event(self, widget, event):
        self.dialog.destroy()

    def on_cancel_clicked(self, widget):
        self.dialog.destroy()

class NewUserDialog(UserForm):
    def __init__(self, bus, account_manager, parent=None):
        super().__init__(bus, account_manager, parent=parent)
        self.mode = 'new'
        self.builder.connect_signals(self)

        # Set some defaults
        self.shells_entry.set_text('/bin/bash')
        self.last_change.set_value(common.days_since_epoch())
        self.set_apply_sensitivity()

        self.dialog.show()

    def on_apply_clicked(self, widget):
        print("clicked with: ", self.username.get_text())
        user = self.account_manager.CreateUser(self.username.get_text(), '')
        # user.name = self.username.get_text()
        # user.rname = self.gc_name.get_text()
        # user.uid = int(self.uid_entry.get_text())
        # user.office = self.gc_office.get_text()
        # user.wphone = self.gc_office_phone.get_text()
        # user.hphone = self.gc_home_phone.get_text()
        # user.other = self.gc_other.get_text()
        # user.directory = self.homedir.get_text()
        # user.shell = self.shells_entry.get_text()
        # user.lstchg = int(self.last_change.get_value())
        # user.min = int(self.minimum.get_value())
        # user.max = int(self.maximum.get_value())
        # user.warn = int(self.warn.get_value())
        # user.inact = int(self.inactive.get_value())
        # user.expire = int(self.expire.get_value())
        # user.password = self.system.encrypt(self.password.get_text())

        # user.groups = [g[0].name for g in self.groups_store if g[2]]
        # user.gid = int(self.pgid.get_text())
        # user.primary_group = self.pgroup.get_text()
        # if self.system.gid_is_free(user.gid):
        #     self.system.add_group(libuser.Group(user.primary_group, user.gid, {}))
        #
        # self.system.add_user(user)
        # if self.builder.get_object('locked_account_check').get_active():
        #     self.system.lock_user(user)
        self.dialog.destroy()

class EditUserDialog(UserForm):
    def __init__(self, bus, account_manager, user, parent=None):
        super().__init__(bus, account_manager, parent=parent)
        self.mode = 'edit'
        self.user = user
        self.builder.connect_signals(self)

        # Do not change the primary group and roles of existing users
        self.builder.get_object('primary_group_grid').set_visible(False)
        self.builder.get_object('role_box').set_visible(False)

        self.username.set_text(user.GetUsername())
        self.password.set_text('\n'*8)
        self.uid_entry.set_text(str(user.GetUID()))
        self.homedir.set_text(user.GetHomeDir())
        self.shells_entry.set_text(user.GetShell())
        rname, office, offphon, homphon, other = user.GetGecos()
        self.gc_name.set_text(rname)
        self.gc_office.set_text(office)
        self.gc_office_phone.set_text(offphon)
        self.gc_home_phone.set_text(homphon)
        self.gc_other.set_text(other)
        # self.last_change.set_value(user.lstchg)
        # self.minimum.set_value(user.min)
        # self.maximum.set_value(user.max)
        # self.warn.set_value(user.warn)
        # self.inactive.set_value(user.inact)
        # self.expire.set_value(user.expire)
        # self.builder.get_object('locked_account_check').set_active(self.system.user_is_locked(user))

        self.pgroup.set_text(self.bus.get_object('io.github.ltsp-manager', user.GetMainGroup()).GetGroupName())
        # Activate the groups in which the user belongs and mark the primary
        for row in self.groups_store:
            if row[0].UsersAreMember(self.username.get_text()):
                row[2] = True
                row[5] = True
            if row[1] == user.GetMainGroup():
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
        # if not '\n' in self.password.get_text():
        #     self.user.password = self.system.encrypt(self.password.get_text())

        self.user.groups = [g[1] for g in self.groups_store if g[2]]
        self.user.gid = int(self.pgid.get_text())
        self.user.primary_group = self.pgroup.get_text()

        self.dialog.destroy()

class ReviewUserDialog(UserForm):
    def __init__(self, bus, account_manager, user, role='', callback=None, parent=None):
        super().__init__(bus, account_manager, parent=parent)
        self.callback = callback
        self.mode = 'new'
        self.user = user
        self.selected_role = role
        self.builder.connect_signals(self)

        self.username.set_text(user.name)
        if user.password not in ['!','*', ''] or user.plainpw:
            self.password.set_text('\n'*8)
            self.password_repeat.set_text('\n'*8)
        self.uid_entry.set_text(str(user.uid))
        self.homedir.set_text(user.directory)
        self.shells_entry.set_text(user.shell)
        self.gc_name.set_text(user.rname)
        self.gc_office.set_text(user.office)
        self.gc_office_phone.set_text(user.wphone)
        self.gc_home_phone.set_text(user.hphone)
        self.gc_other.set_text(user.other)
        self.last_change.set_value(user.lstchg)
        self.minimum.set_value(user.min)
        self.maximum.set_value(user.max)
        self.warn.set_value(user.warn)
        self.inactive.set_value(user.inact)
        self.expire.set_value(user.expire)
        self.builder.get_object('locked_account_check').set_active(user.password[0] == '!')

        self.pgroup.set_text(user.primary_group)
        self.pgid.set_text(str(user.gid))
        # Activate the groups in which the user belongs and mark the primary
        for row in self.groups_store:
            for gr in user.groups:
                if gr == row[0].name:
                    row[2] = True
                    row[5] = True
            if row[1] == user.primary_group:
                self.primary_group = row
                self.set_group_primary(row)

        if role:
            for r in self.role_combo.get_model():
                if r[0] == role:
                    self.role_combo.set_active_iter(r.iter)
                    break

        self.dialog.show()

    def on_apply_clicked(self, widget):
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

        self.user.groups = [g[1] for g in self.groups_store if g[2]]
        self.user.gid = int(self.pgid.get_text())
        self.user.primary_group = self.pgroup.get_text()

        if self.builder.get_object('locked_account_check').get_active():
            if self.user.password[0] != '!':
                self.user.password = '!'+self.user.password
        self.dialog.destroy()
        if self.callback:
            self.callback(self.selected_role)
