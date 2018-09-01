#!/usr/bin/env python3
# Copyright (C) 2012-2017 Alkis Georgopoulos <alkisg@gmail.com>
# 2012-2015, Fotis Tsamis <ftsamis@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import getpass
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import glob
import locale
import os
import socket
import subprocess
import sys
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
from twisted.internet import gtk3reactor
gtk3reactor.install()
from twisted.internet import reactor, defer

import about_dialog
import common
import config
import create_users
import dialogs
import export_dialog
import group_form
import import_dialog
import ip_dialog
import libuser
import ltsp_info
import parsers
import ltsp_shared_folders
import user_form
import version

class Gui:
    def __init__(self):
        self.system = libuser.system
        self.sf=ltsp_shared_folders.SharedFolders(self.system)
        self.conf = config.parser

        self.builder = Gtk.Builder()
        self.builder.add_from_file('ltsp-manager.ui')
        self.builder.connect_signals(self)

        self.main_window = self.builder.get_object('main_window')
        self.users_tree = self.builder.get_object('users_treeview')
        self.groups_tree = self.builder.get_object('groups_treeview')
        self.users_sort = self.builder.get_object('users_sort')
        self.groups_sort = self.builder.get_object('groups_sort')
        self.users_filter = self.builder.get_object('users_filter')
        self.groups_filter = self.builder.get_object('groups_filter')
        self.users_model = self.builder.get_object('users_store')
        self.groups_model = self.builder.get_object('groups_store')

        self.show_private_groups = False
        self.show_system_groups = False
        self.builder.get_object('mi_show_private_groups').set_active(self.conf.getboolean('GUI', 'show_private_groups'))
        self.builder.get_object('mi_show_system_groups').set_active(self.conf.getboolean('GUI', 'show_system_groups'))
        if locale.getdefaultlocale()[0] != "el_GR":
            self.builder.get_object("mn_server").remove(self.builder.get_object('mi_configuration_network'))
            self.builder.get_object("mn_help").remove(self.builder.get_object('mi_helpdesk_ticket'))
            self.builder.get_object("mn_help").remove(self.builder.get_object('mi_forum'))

        self.users_filter.set_visible_func(self.set_user_visibility)
        self.groups_filter.set_visible_func(self.set_group_visibility)

        # Fill the View -> Columns menu with all the columns of the treeview
        mn_view_columns = self.builder.get_object('mn_view_columns')
        users_columns = self.users_tree.get_columns()

        visible = self.conf.get('GUI', 'visible_user_columns')
        if visible == 'all':
            visible = [c.get_title() for c in users_columns]
        else:
            visible = visible.split(',')
        for column in users_columns:
            title = column.get_title()
            menuitem = Gtk.CheckMenuItem(title)
            menuitem.connect('toggled', self.on_mi_view_column_toggled, column)
            menuitem.set_active(title in visible)
            mn_view_columns.append(menuitem)
        self.populate_treeviews()

        self.queue = []
        self.system.connect_event(self.on_libuser_changed)
        self.main_window.show_all()
        self.check_initial_setup()

## General helper functions

    def edit_file(self, filename):
        subprocess.Popen(['xdg-open', filename], stdin=open(os.devnull))
        # TODO: Maybe throw an error message if not os.path.isfile(filename)
        # TODO: ltsp-manager doesn't exit until the spawned FDs are closed

    def run_as_sudo_user(self, cmd):
        print(('EXECUTE:\t' + '\t'.join(cmd)))
        sys.stdout.flush()

    def open_link(self, link):
        self.run_as_sudo_user(['xdg-open', link])

    def get_selected_users(self):
        selection = self.users_tree.get_selection()
        paths = selection.get_selected_rows()[1]
        selected = [self.users_sort[path][0] for path in paths]
        return selected

    def get_selected_groups(self):
        selection = self.groups_tree.get_selection()
        paths = selection.get_selected_rows()[1]
        selected = [self.groups_sort[path][0] for path in paths]
        return selected

## INotify

    def on_libuser_changed(self, event):
        self.queue.append(event)
        d = defer.Deferred()
        reactor.callLater(1, d.callback, len(self.queue))
        d.addCallback(self.check_libuser_events)
            
    def check_libuser_events(self, len_queue):
        if len_queue == len(self.queue): 
            self.queue = []
            self.repopulate_treeviews()
    
## Groups and users treeviews

    def populate_treeviews(self):
        """Fill the users and groups treeviews from the system"""
        for user in self.system.users.values():
            self.users_model.append([user, user.uid, user.name, user.primary_group, user.rname, user.office, user.wphone, user.hphone, user.other, user.directory, user.shell, user.lstchg, user.min, user.max, user.warn, user.inact, user.expire])
        for group in self.system.groups.values():
            self.groups_model.append([group, group.gid, group.name])

    def repopulate_treeviews(self):
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

    def set_user_visibility(self, model, rowiter, options):
        user = model[rowiter][0]
        selected = self.get_selected_groups()
        # FIXME: The list comprehension here costs
        return (len(selected) == 0 and (self.show_system_groups or not user.is_system_user())) \
                or user in [u for g in selected for u in g.members.values()]

    def set_group_visibility(self, model, rowiter, options):
        group = model[rowiter][0]
        return (self.show_private_groups or not group.is_private()) and (self.show_system_groups or group.is_user_group())

    def on_groups_selection_changed(self, selection):
        self.users_filter.refilter()
        mi_edit_group = self.builder.get_object('mi_edit_group')
        mi_delete_group = self.builder.get_object('mi_delete_group')
        rows = selection.count_selected_rows()
        if rows == 0:
            mi_edit_group.set_sensitive(False)
            mi_delete_group.set_sensitive(False)
        elif rows == 1:
            mi_edit_group.set_sensitive(True)
            mi_edit_group.set_label(_("Edit group..."))
            mi_delete_group.set_label(_("Delete group..."))
            mi_delete_group.set_sensitive(True)
        else:
            mi_edit_group.set_sensitive(False)
            mi_delete_group.set_label(_("Delete groups..."))
            mi_delete_group.set_sensitive(True)

    def on_users_selection_changed(self, selection):
        mi_edit_user = self.builder.get_object('mi_edit_user')
        mi_delete_user = self.builder.get_object('mi_delete_user')
        mi_remove_user = self.builder.get_object('mi_remove_user')
        rows = selection.count_selected_rows()
        if rows == 0:
            mi_edit_user.set_sensitive(False)
            mi_delete_user.set_sensitive(False)
            mi_remove_user.set_sensitive(False)
        else:
            if self.groups_tree.get_selection().count_selected_rows() > 0:
                mi_remove_user.set_sensitive(True)
            else:
                mi_remove_user.set_sensitive(False)

            mi_delete_user.set_sensitive(True)

            if rows == 1:
                mi_edit_user.set_sensitive(True)
                mi_edit_user.set_label(_("Edit user..."))
                mi_delete_user.set_label(_("Delete user..."))
            else:
                mi_edit_user.set_sensitive(False)
                mi_delete_user.set_label(_("Delete users..."))


    def on_users_tv_button_press_event(self, widget, event):
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))

        if event.button == 3:
            menu = self.builder.get_object('mn_users').popup(None, None, None, None, event.button, event.time)
            selection = widget.get_selection()
            selected = selection.get_selected_rows()[1]
            if clicked:
                clicked = clicked[0]
                if clicked not in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()
            return True

    def on_groups_tv_button_press_event(self, widget, event):
        clicked = widget.get_path_at_pos(int(event.x), int(event.y))

        if event.button == 3:
            menu = self.builder.get_object('mn_groups').popup(None, None, None, None, event.button, event.time)
            selection = widget.get_selection()
            selected = selection.get_selected_rows()[1]
            if clicked:
                clicked = clicked[0]
                if clicked not in selected:
                    selection.unselect_all()
                    selection.select_path(clicked)
            else:
                selection.unselect_all()
            return True

    def on_users_treeview_row_activated(self, widget, path, column):
        user_form.EditUserDialog(self.system, widget.get_model()[path][0], parent=self.main_window)

    def on_groups_treeview_row_activated(self, widget, path, column):
        group_form.EditGroupDialog(self.system, self.sf, widget.get_model()[path][0], parent=self.main_window)
    
    def on_unselect_all_groups_clicked(self, widget):
        self.groups_tree.get_selection().unselect_all()
    
    def on_main_window_delete_event(self, widget, event):
        self.conf.set('GUI', 'show_private_groups', str(self.show_private_groups))
        self.conf.set('GUI', 'show_system_groups', str(self.show_system_groups))
        visible_cols = [col.get_title() for col in self.users_tree.get_columns() if col.get_visible()]
        # TODO: restore this when LP: #1710416 is fixed
        self.conf.set('GUI', 'visible_user_columns', 'all')
        config.save()
        exit()

## File menu

    def on_mi_signup_activate(self, widget):
        subprocess.Popen(['./signup_server.py'])
        
    #FIXME: Maybe use notify /etc/group then self.populate_treeviews not need to 
    #update user groups for shared folder library
    def on_mi_new_users_activate(self, widget):
        create_users.NewUsersDialog(self.system, self.sf, self.main_window)
    
    def on_mi_import_passwd_activate(self, widget):
        chooser = Gtk.FileChooserDialog(title=_("Select the passwd file to import"), 
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        chooser.set_transient_for(self.main_window)
        chooser.set_icon_from_file('../pixmaps/ltsp-manager.svg')
        chooser.set_default_response(Gtk.ResponseType.OK)
        homepath = os.path.expanduser('~')
        chooser.set_current_folder(homepath)
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            passwd = chooser.get_filename()
            path = os.path.dirname(passwd)
            shadow = os.path.join(path, 'shadow')
            group = os.path.join(path, 'group')
            if not os.path.isfile(shadow):
                shadow = None
            if not os.path.isfile(group):
                group = None
            new_users = parsers.passwd().parse(passwd, shadow, group)
            if len(new_users.users) == 0:
                text = _("The file \"%s\" contains no data.") % passwd
                dialogs.ErrorDialog(text, _("Error")).showup()
                return False
            chooser.destroy()
            import_dialog.ImportDialog(new_users, parent=self.main_window)
        else:
            chooser.destroy()
    
    def on_mi_import_csv_activate(self, widget):
        chooser = Gtk.FileChooserDialog(title=_("Select the CSV file to import"), 
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        chooser.set_transient_for(self.main_window)
        chooser.set_icon_from_file('../pixmaps/ltsp-manager.svg')
        chooser.set_default_response(Gtk.ResponseType.OK)
        homepath = os.path.expanduser('~')
        chooser.set_current_folder(homepath)
        resp = chooser.run()
        if resp == Gtk.ResponseType.OK:
            fname = chooser.get_filename()
            new_users = parsers.CSV().parse(fname)
            if len(new_users.users) == 0:
                text = _("The file \"%s\" contains no data.") % fname
                dialogs.ErrorDialog(text, _("Error")).showup()
                return False
            chooser.destroy()
            import_dialog.ImportDialog(new_users, parent=self.main_window)
        else:
            chooser.destroy()
    
    def on_mi_export_csv_activate(self, widget):
        users = self.get_selected_users()
        if len(users) == 0:
            if self.show_system_groups:
                users = self.system.users.values()
            else:
                users = [u for u in self.system.users.values() if not u.is_system_user()]
        export_dialog.ExportDialog(self.main_window, self.system, users)

## Server menu

    def check_initial_setup(self):
        if common.run_command(['./initial-setup.sh', '--check'])[0]:
            return
        message = "You need to run the initial LTSP setup actions."
        second_message = _("LTSP Manager has detected that you either haven't yet run the initial LTSP setup, or that you upgraded to a new version and you need to run it again.") + \
            "\n\n" + _("Should LTSP Manager run initial-setup?")
        dlg = dialogs.AskDialog(message, title="Initial LTSP setup", parent=self.main_window)
        dlg.format_secondary_text(second_message)
        response = dlg.showup()
        if response == Gtk.ResponseType.YES:
            subprocess.Popen(['./run-in-terminal.sh', './initial-setup.sh', '--no-prompt'])

    def on_mi_initial_setup_activate(self, widget):
        subprocess.Popen(['./run-in-terminal.sh', './initial-setup.sh'])

    def on_mi_configuration_network_activate(self, widget):
        ip_dialog.Ip_Dialog(self.main_window)

    def on_mi_ltsp_update_image_activate(self, widget):
        message = _("Are you sure you want to update the LTSP image?")
        second_message = _("Depending on the CPU speed and image size, this may need about 10 minutes. After that, (re)boot your workstations.")
        dlg = dialogs.AskDialog(message, parent=self.main_window)
        dlg.format_secondary_text(second_message)
        response = dlg.showup()
        if response == Gtk.ResponseType.YES:        
            subprocess.Popen(['./run-in-terminal.sh', 'ltsp-update-image', '--cleanup', '/'])

    def on_mi_ltsp_revert_image_activate(self, widget):
        message = _("Are you sure you want to revert to the previous version of the LTSP image?")
        dlg = dialogs.AskDialog(message, parent=self.main_window)
        response = dlg.showup()
        if response == Gtk.ResponseType.YES: 
            subprocess.Popen(['./run-in-terminal.sh', 'ltsp-update-image', '--revert', '/'])

    def on_mi_edit_lts_conf_activate(self, widget):
        for f in glob.glob('/var/lib/tftpboot/ltsp/*/lts.conf'):
            self.edit_file(f)

    def on_mi_edit_pxelinux_cfg_activate(self, widget):
        for f in glob.glob('/var/lib/tftpboot/ltsp/*/pxelinux.cfg/default'):
            self.edit_file(f)

    def on_mi_edit_ltsp_shared_folders_activate(self, widget):
        self.edit_file('/etc/default/ltsp-shared-folders')

    def on_mi_edit_dnsmasq_conf_activate(self, widget):
        self.edit_file('/etc/dnsmasq.d/ltsp-server-dnsmasq.conf')

## View menu

    def on_mi_view_column_toggled(self, checkmenuitem, treeviewcolumn):
        treeviewcolumn.set_visible(checkmenuitem.get_active())

    def on_mi_show_system_groups_toggled(self, widget):
        self.show_system_groups = not self.show_system_groups
        self.groups_filter.refilter()
        self.users_filter.refilter()

    def on_mi_show_private_groups_toggled(self, widget):
        self.show_private_groups = not self.show_private_groups
        self.groups_filter.refilter()

    def on_mi_refresh_activate(self, widget):
        self.repopulate_treeviews()

## Users menu

    def on_mi_new_user_activate(self, widget):
        user_form.NewUserDialog(self.system, parent=self.main_window)

    def on_mi_edit_user_activate(self, widget):
        user_form.EditUserDialog(self.system, self.get_selected_users()[0], parent=self.main_window)

    def on_mi_delete_user_activate(self, widget):
        users = self.get_selected_users()
        users_n = len(users)
        if users_n == 1:
            message = _("Are you sure you want to delete user \"%s\"?") % users[0].name
            homes_message = _("Also delete the user's home directory.")
            homes_warn = _("WARNING: if you enable this option, the user's home directory with all its files will be deleted, along with the user's e-mail at /var/mail, if it exists")
        else:
            message = _("Are you sure you want to delete the following %d users?") % users_n
            message += "\n" + ', '.join([user.name for user in users])
            homes_message = _("Also delete the users' home directories.")
            homes_warn = _("WARNING: if you enable this option, the users' home directories with all their files will be deleted, along with the users' e-mails at /var/mail, if they exist")
        homes_warn += "\n\n" + _("This action can't be undone.")
        
        dlg = dialogs.AskDialog(message, parent=self.main_window)
        vbox = dlg.get_message_area()
        rm_homes_check = Gtk.CheckButton(homes_message)
        rm_homes_check.get_child().set_tooltip_text(homes_warn) 
        rm_homes_check.show()
        vbox.pack_start(rm_homes_check, False, False, 12)
        response = dlg.showup()
        if response == Gtk.ResponseType.YES:
            rm_homes = rm_homes_check.get_active()
            if users_n > 1:
                progress = dialogs.ProgressDialog("Deleting Users", users_n, self.main_window)
                for user in self.get_selected_users():
                    dialogs.wait_gtk()
                    progress.set_message("Delete user: {user}".format(user=user.name))
                    self.system.delete_user(user, rm_homes)
                    progress.inc()
            else:
                self.system.delete_user(users[0],rm_homes)
            
    def on_mi_remove_user_activate(self, widget):
        users = self.get_selected_users()
        groups = self.get_selected_groups()
        users_n = len(users)
        group_names = ', '.join([group.name for group in groups])
        if users_n == 1:
            message = _("Are you sure you want to remove user %(user)s from the selected groups (%(groups)s)?") % {"user":users[0].name, "groups":group_names}
        else:
            message = _("Are you sure you want to remove the following %(count)d users from the selected groups (%(groups)s)?") % {"count":users_n, "groups":group_names}
            message += "\n" + ', '.join([user.name for user in users])

        response = dialogs.AskDialog(message, parent=self.main_window).showup()
        if response == Gtk.ResponseType.YES:
            if users_n > 1:
                progress = dialogs.ProgressDialog("Remove users from groups", users_n, self.main_window)
                for user in self.get_selected_users():
                    dialogs.wait_gtk()
                    progress.set_message("remove user {user} from groups {groups}".format(user=user.name, groups=', '.join([g.name for g in groups])))
                    self.system.remove_user_from_groups(user, groups)
                    progress.inc()
            else:
                self.system.remove_user_from_groups(users[0], groups)

## Groups menu

    def on_mi_new_group_activate(self, widget):
        group_form.NewGroupDialog(self.system, self.sf, parent=self.main_window)

    def on_mi_edit_group_activate(self, widget):
        group_form.EditGroupDialog(self.system, self.sf, self.get_selected_groups()[0], parent=self.main_window)

    def on_mi_delete_group_activate(self, widget):
        groups = self.get_selected_groups()
        groups_n = len(groups)
        if groups_n == 1:
            message = _("Are you sure you want to delete group %s?") % groups[0].name
        else:
            message = _("Are you sure you want to delete the following %d groups?") % groups_n
            message += "\n" + ', '.join([group.name for group in groups])

        response = dialogs.AskDialog(message, parent=self.main_window).showup()
        if response == Gtk.ResponseType.YES:
            self.sf.remove(groups)
            progress = dialogs.ProgressDialog("Deleting Groups", users_n, self.main_window)
            for group in groups:
                dialogs.wait_gtk()
                progress.set_message("Deleting group {group}".format(group=group.name))
                self.system.delete_group(group)
                progress.inc()

## Help menu

    def on_mi_home_activate(self, widget):
        if locale.getdefaultlocale()[0] != "el_GR":
            self.open_link('http://wiki.ltsp.org/wiki/Ltsp-manager')
        else:
            self.open_link('http://ts.sch.gr/wiki/Linux/LTSP')

    def on_mi_report_bug_activate(self, widget):
        self.open_link('https://bugs.launchpad.net/ltsp-manager')

    def on_mi_ask_question_activate(self, widget):
        self.open_link('https://answers.launchpad.net/ltsp-manager')
    
    def on_helpdesk_ticket_activate(self, widget):
        self.open_link('http://helpdesk.sch.gr/ticketnew_user.php?category_id=9017')
    
    def on_mi_irc_activate(self, widget):
        host = socket.gethostname()
        user = getpass.getuser()
        if user == "root":
            try:
                user = os.getlogin()
            except:
                user = os.getenv("SUDO_USER")
        lang = locale.getdefaultlocale()[0]
        self.open_link("http://ts.sch.gr/repo/irc?user=%s&host=%s&lang=%s" % \
                       (user, host, lang))

    def on_mi_forum_activate(self, widget):
        self.open_link('http://alkisg.mysch.gr/steki/index.php?board=67.0')

    def on_mi_map_activate(self, widget):
        print((locale.getdefaultlocale()[0]))
        if locale.getdefaultlocale()[0] != "el_GR":
            self.open_link('http://www.ltsp.org/stories/worldmap/')
        else:
            self.open_link('http://ts.sch.gr/wiki/Linux/LTSP/Προχωρημένα/Χάρτης')

    def on_mi_lts_conf_manpage_activate(self, widget):
        self.open_link('http://manpages.ubuntu.com/lts.conf')

    def on_mi_ltsp_info_activate(self, widget):
        ltsp_info.LtspInfo(self.main_window)

    def on_mi_about_activate(self, widget):
        about_dialog.AboutDialog(self.main_window)


# To export a man page:
# help2man -L el -s 8 -o ltsp-manager.8 -N ./ltsp-manager && man ./ltsp-manager.8
def usage():
    print(_("""Usage: ltsp-manager [OPTIONS]

It depends on a set of packages suitable for configuring LTSP in small
computer labs, and it provides a GUI for managing user accounts, running
maintenance tasks etc.

Options:
    -h, --help     Display this help and exit.
    -v, --version  Output version information and exit.

Bug reports can be filed at https://bugs.launchpad.net/ltsp-manager."""))


def print_version():
    print(_("""ltsp-manager %s
Copyright (C) 2009-2017 Alkis Georgopoulos <alkisg@gmail.com>, Fotis Tsamis <ftsamis@gmail.com>.
License GPLv3+: GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>.

Authors: Alkis Georgopoulos <alkisg@gmail.com>, Fotis Tsamis <ftsamis@gmail.com>.""") % version.__version__)

if __name__ == '__main__':
    if len(sys.argv) == 2 and (sys.argv[1] == '-v' or sys.argv[1] == '--version'):
        print_version()
        sys.exit(0)
    elif len(sys.argv) == 2 and (sys.argv[1] == '-h' or sys.argv[1] == '--help'):
        usage()
        sys.exit(0)
    elif len(sys.argv) >= 2:
        usage()
        sys.exit(1)
    Gui()
    reactor.run()
