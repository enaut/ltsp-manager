
import sys
import os
import locale
from gettext import gettext as _


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, Gio

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
import dbus

import common
import config
import dialogs
import version
import paths

import group_form
import user_form
import create_users
import import_dialog


class Gui():
    """The base class and window of LTSP-manager"""

    def __init__(self):
        self.dbus = dbus.SystemBus()
        self.account_manager = self.dbus.get_object('io.github.ltsp-manager', paths.ACCOUNTMANAGER_PATH)

        self.conf = config.get_config()
        self.path = os.path.dirname(os.path.realpath(__file__))

        # Prepare the Ressources
        resource = Gio.resource_load(os.path.join(paths.pkgdatadir, 'ltsp-manager.gresource'))
        Gio.Resource._register(resource)

        # Load the UI
        self.builder = Gtk.Builder()
        self.builder.add_from_resource('/org/ltsp/ltsp-manager/ui/ltsp19.ui')
        self.builder.connect_signals(self)
        self.icontheme = Gtk.IconTheme.get_default()

        # Load the components
        self.load_components()

        self.setup_user_group_visibility()

        self.setup_column_visibility()

        self.populate_treeviews()

        self.account_manager.connect_to_signal("on_users_changed", self.on_users_changed, dbus_interface="io.github.ltsp.manager.AccountManager")
        self.account_manager.connect_to_signal("on_groups_changed", self.on_groups_changed, dbus_interface="io.github.ltsp.manager.AccountManager")
        self.on_users_selection_changed()
        self.on_groups_selection_changed()

        self.main_window.set_default_size(-1, 600)
        self.main_window.connect("destroy", self.on_main_window_delete_event)
        self.main_window.show_all()

    def load_components(self):
        """ Load the components from the UI file """
        self.main_window = self.builder.get_object('main_window')
        self.users_tree = self.builder.get_object('users_treeview')
        self.groups_tree = self.builder.get_object('groups_treeview')
        self.users_sort = self.builder.get_object('users_sort')
        self.groups_sort = self.builder.get_object('groups_sort')
        self.users_filter = self.builder.get_object('users_filter')
        self.groups_filter = self.builder.get_object('groups_filter')
        self.users_model = self.builder.get_object('users_store')
        self.groups_model = self.builder.get_object('groups_store')

    def setup_column_visibility(self):
        """ Load the visible columns from last time from config
            If no config is found everything is visible
            Create the menu entries for each column"""
        mn_view_columns = self.builder.get_object('mn_visible_user_columns')
        users_columns = self.users_tree.get_columns()

        visible = self.conf.parser.get('GUI', 'visible_user_columns')
        if visible == 'all':
            visible = [c.get_title() for c in users_columns]
        else:
            visible = visible.split(',')
        for column in users_columns:
            title = column.get_title()
            checkbutton = Gtk.CheckButton(label=title)
            checkbutton.connect('toggled', self.on_mi_view_column_toggled, column)
            checkbutton.set_active(title in visible)
            checkbutton.set_visible(True)
            mn_view_columns.pack_start(checkbutton, True, True, 0)

    def setup_user_group_visibility(self):
        """Setup the filter functions so that when a group is selected only the users from this group are displayed
        Also this filters system groups and private groups if the Configuration is set accordingly"""
        self.show_private_groups = self.conf.parser.getboolean('GUI', 'show_private_groups')
        self.show_system_groups = self.conf.parser.getboolean('GUI', 'show_system_groups')
        self.builder.get_object('conf_show_private_groups').set_active(self.show_private_groups)
        self.builder.get_object('conf_show_system_groups').set_active(self.show_system_groups)

        self.users_filter.set_visible_func(self.set_user_visibility)
        self.groups_filter.set_visible_func(self.set_group_visibility)

    def set_user_visibility(self, model, rowiter, options):
        """ Hide the Users that are not part of the selected groups
            Also if show_system_groups is not toggled system users are not displayed """
        user = model[rowiter][0]
        selected = self.get_selected_groups()
        if self.show_system_groups or not user.IsSystemUser():
            if len(selected) == 0:
                return True
            if user.IsPartOfGroups(selected):
                return True
        return False

    def set_group_visibility(self, model, rowiter, options):
        """ Hide the groups according to the show_system_groups and show_private_groups setting. """
        group = model[rowiter][0]
        if self.show_private_groups and self.show_system_groups:
            return True
        if not (group.IsPrivateGroup() or group.IsSystemGroup()):
            return True
        if (self.show_private_groups and group.IsPrivateGroup()) or (self.show_system_groups and group.IsSystemGroup()):
            return True
        return False

    def on_conf_show_private_groups_toggled(self, checker):
        """React to a change of the show_private_groups setting"""
        self.show_private_groups = checker.get_active()
        self.conf.parser.set('GUI', 'show_private_groups', "yes" if checker.get_active() else "no")
        self.conf.save()
        self.groups_filter.refilter()
        self.users_filter.refilter()

    def on_conf_show_system_groups_toggled(self, checker):
        """React to a change of the show_system_groups setting"""
        self.show_system_groups = checker.get_active()
        self.conf.parser.set('GUI', 'show_system_groups', "yes" if checker.get_active() else "no")
        self.conf.save()
        self.groups_filter.refilter()
        self.users_filter.refilter()

    def populate_treeviews(self):
        """Fill the users and groups treeviews from the DBUS-service"""
        for userpath in self.account_manager.ListUsers():
            user = self.dbus.get_object('io.github.ltsp-manager', userpath)
            values = list(user.GetValues())
            self.users_model.append([user] + values)

        for group_path in self.account_manager.ListGroups():
            group = self.dbus.get_object('io.github.ltsp-manager', group_path)
            group_gid, group_name = group.GetValues()
            self.groups_model.append([group, group_gid, group_name])

    def repopulate_treeviews(self):
        """After a change of users it is easiest to just completely repopulate the treeviews
        This function preserves the selectd users and groups when possible"""
        # Preserve the selected groups and users
        groups_selection = self.groups_tree.get_selection()
        users_selection = self.users_tree.get_selection()
        selected_groups = [i.name for i in self.get_selected_groups()]
        selected_users = [i.name for i in self.get_selected_users()]

        # Clear and refill the treeviews
        self.users_model.clear()
        self.groups_model.clear()
        self.populate_treeviews()

        # Reselect the previously selected groups and users, if possible
        groups_iters = dict((row[0].name, row.iter) for row in self.groups_sort)
        for gname in selected_groups:
            if gname in groups_iters:
                groups_selection.select_iter(groups_iters[gname])
        users_iters = dict((row[0].name, row.iter) for row in self.users_sort)
        for uname in selected_users:
            if uname in users_iters:
                users_selection.select_iter(users_iters[uname])
        self.groups_filter.refilter()
        self.users_filter.refilter()

    def on_mi_view_column_toggled(self, checkmenuitem, treeviewcolumn):
        """ React to show/hide of user columns
            Store the new selection in the config file
        """
        treeviewcolumn.set_visible(checkmenuitem.get_active())
        visible_cols = [col.get_title() for col in self.users_tree.get_columns() if col.get_visible()]
        self.conf.parser.set('GUI', 'visible_user_columns', ','.join(visible_cols))
        self.conf.save()

    def on_groups_selection_changed(self, selection=None):
        """ Filter the users according to the selected group
            Enable, disable and rename the group editing buttons.
            """
        self.users_filter.refilter()
        edit_group = self.builder.get_object('edit_group')
        delete_group = self.builder.get_object('delete_group')
        if selection:
            rows = selection.count_selected_rows()
        else:
            rows = 0
        if rows == 0:
            edit_group.set_sensitive(False)
            delete_group.set_sensitive(False)
        elif rows == 1:
            edit_group.set_sensitive(True)
            edit_group.set_label(_("Edit group"))
            delete_group.set_label(_("Delete group"))
            delete_group.set_sensitive(True)
        else:
            edit_group.set_sensitive(False)
            delete_group.set_label(_("Delete groups"))
            delete_group.set_sensitive(True)

    def on_users_selection_changed(self, selection=None):
        """Enable disable and rename the User Editing buttons"""
        edit_user = self.builder.get_object('edit_user')
        delete_user = self.builder.get_object('delete_user')
        if selection:
            rows = selection.count_selected_rows()
        else:
            rows = 0
        if rows == 0:
            edit_user.set_sensitive(False)
            delete_user.set_sensitive(False)
        else:

            delete_user.set_sensitive(True)

            if rows == 1:
                edit_user.set_sensitive(True)
                edit_user.set_label(_("Edit user"))
                delete_user.set_label(_("Delete user"))
            else:
                edit_user.set_sensitive(False)
                delete_user.set_label(_("Delete users"))

    def on_unselect_all_groups_clicked(self, widget):
        """Unselect all groups"""
        self.groups_tree.get_selection().unselect_all()

    @staticmethod
    def on_main_window_delete_event(event):
        """ Cleanup on close of Ltsp-Manager """
        Gtk.main_quit()
        sys.exit()

    def get_selected_users(self):
        """ Get the users that are selected in the pane """
        selection = self.users_tree.get_selection()
        pathlist = selection.get_selected_rows()[1]
        selected = [self.users_sort[path][0] for path in pathlist]
        return selected

    def get_selected_groups(self):
        """ Get the groups that are selected in the pane """
        selection = self.groups_tree.get_selection()
        pathlist = selection.get_selected_rows()[1]
        selected = [self.groups_sort[path][0] for path in pathlist]
        return selected

    def on_users_changed(self):
        print("Updating Users!")
        self.repopulate_treeviews()

    def on_groups_changed(self):
        print("Updating Groups!")
        self.repopulate_treeviews()

    def on_add_user_clicked(self, widget):
        user_form.NewUserDialog(self.dbus, self.account_manager, parent=self.main_window)

    def on_batch_add_users_clicked(self, widget):
        create_users.NewUsersDialog(self.dbus, self.account_manager, parent=self.main_window)

    def on_import_users_clicked(self, widget):
        import_dialog.ImportAssistant(self.dbus, self.account_manager, parent=self.main_window)

    def on_edit_user_clicked(self, widget):
        user_form.EditUserDialog(self.dbus, self.account_manager, parent=self.main_window)

    def on_delete_user_clicked(self, widget):
        """ When the user clicks on delete user(s) a warning dialog is shown.
            If confirmed the users are deleted with the remove home checkbox considered
            If more than one user is deleted a ProgressDialog is shown.
            """
        users = self.get_selected_users()
        users_n = len(users)
        if users_n == 1:
            message = _("Are you sure you want to delete user \"%s\"?") % users[0].GetUsername()
            homes_message = _("Also delete the user's home directory.")
            homes_warn = _("WARNING: if you enable this option, the user's home directory with all its files will be deleted,"
                           " along with the user's e-mail at /var/mail, if it exists")
        else:
            message = _("Are you sure you want to delete the following %d users?") % users_n
            message += "\n\n" + ', '.join([user.GetUsername() for user in users])
            homes_message = _("Also delete the users' home directories.")
            homes_warn = _("WARNING: if you enable this option, the users' home directories with all their files will be deleted,"
                           " along with the users' e-mails at /var/mail, if they exist")
        homes_warn += "\n\n" + _("This action cannot be undone.")

        dlg = dialogs.AskDialog(message, parent=self.main_window)
        vbox = dlg.get_message_area()
        rm_homes_check = Gtk.CheckButton(label=homes_message)
        rm_homes_check.get_child().set_tooltip_text(homes_warn)
        rm_homes_check.show()
        vbox.pack_start(rm_homes_check, False, False, 12)
        response = dlg.showup()
        if response == Gtk.ResponseType.YES:
            rm_homes = rm_homes_check.get_active()
            if users_n > 1:
                progress = dialogs.ProgressDialog("Deleting Users",
                                                  users_n,
                                                  self.main_window,
                                                  success_label="Users were deleted:\n\n" + ", ".join([user.GetUsername() for user in users]))
                for user in self.get_selected_users():
                    dialogs.wait_gtk()
                    progress.set_message("Delete user: {user}".format(user=user.GetUsername()))
                    user.DeleteUser(rm_homes)
                    progress.inc()
            else:
                users[0].DeleteUser(rm_homes)

    def on_add_group_clicked(self, widget):
        group_form.NewGroupDialog(self.dbus, self.account_manager, self.main_window)

    def on_edit_group_clicked(self, widget):
        groups = self.get_selected_groups()
        if len(groups) == 1:
            group_form.EditGroupDialog(groups[0], self.dbus, self.account_manager, self.main_window)

    def on_delete_group_clicked(self, widget):
        groups = self.get_selected_groups()
        groups_n = len(groups)
        if groups_n == 1:
            message = _("Are you sure you want to delete group %s?") % groups[0].GetGroupName()
        else:
            message = _("Are you sure you want to delete the following %d groups?") % groups_n
            message += "\n" + ', '.join([group.GetGroupName() for group in groups])

        response = dialogs.AskDialog(message, parent=self.main_window).showup()
        if response == Gtk.ResponseType.YES:
            progress = dialogs.ProgressDialog("Deleting Groups", groups_n, self.main_window)
            for group in groups:
                dialogs.wait_gtk()
                progress.set_message("Deleting group {group}".format(group=group.GetGroupName()))
                try:
                    group.DeleteGroup()
                except dbus.DBusException as error:
                    progress.set_error(str(error))
                    break
                progress.inc()


Gui()
Gtk.main()
