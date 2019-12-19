#!/usr/bin/env python3

# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.
import os
import grp
import pwd
import re
from gettext import gettext as _

from gi.repository import GLib
import dbus
import dbus.service
import dbus.mainloop.glib


import common
import version

objects = {  # will be populated with: dbus-path:object
}


FIRST_SYSTEM_UID = 0
LAST_SYSTEM_UID = 999

FIRST_SYSTEM_GID = 0
LAST_SYSTEM_GID = 999

FIRST_UID = 1000
LAST_UID = 29999

FIRST_GID = 1000
LAST_GID = 29999

NAME_REGEX = "^[a-z][-a-z0-9_]*$"


class UserException(dbus.DBusException):
    """This exception is thrown whenever an error with a user happens."""
    _dbus_error_name = 'io.github.ltsp.manager.UserException'


class GroupException(dbus.DBusException):
    """This exception is thrown whenever an error with a user happens."""
    _dbus_error_name = 'io.github.ltsp.manager.GroupException'


class PermissionDeniedException(dbus.DBusException):
    """This exception is thrown whenever an a Permission was denied."""
    _dbus_error_name = 'io.github.ltsp.manager.PermissionDeniedException'


def authorize(sender, errormessage):
    """check Authorization with following parameters in d-feet:
    ('system-bus-name', {'name' :  GLib.Variant("s",':1.13424')}), 'io.github.ltsp-manager.accountmanager.createuser', {}, 1, ''"""
    subject = ('system-bus-name', {'name': sender})
    action_id = "io.github.ltsp-manager.accountmanager"
    details = {}
    flags = 1
    cancellation_id = ''
    auth = polkit.CheckAuthorization(subject, action_id, details, flags, cancellation_id)
    if not auth[0]:
        print("Authentication not granted: ", errormessage, auth)
        print(auth[0])
        raise PermissionDeniedException(_("Authentication was not possible: {}").format(errormessage))
    return auth


class AccountManager(dbus.service.Object):
    """This class is used to manage Unix useraccounts via DBUS"""

    def __init__(self, *args):
        super().__init__(*args)
        users = self.load_users()
        groups = self.load_groups()
        self.load_group_members(groups)
        self.load_user_groups(users)
        self.on_users_changed()

    @staticmethod
    def _filter_(prefix):
        ret = []
        for key in objects:
            if key.startswith(prefix):
                ret.append(key)
        return ret

    @staticmethod
    def load_groups(group=None):
        """Load all the groups from system configuration"""
        ret_groups = []
        groups = [grp.getgrnam(group)] if group else grp.getgrall()
        for group_sys in groups:
            path = "/Group/{}".format(group_sys.gr_gid)
            if path not in objects:
                group_obj = Group(system_bus, path).load(group_sys.gr_gid)
                objects[path] = group_obj
            ret_groups.append(path)
        return ret_groups

    @staticmethod
    def load_users(user=None):
        """Load all the users from system configuration"""
        ret_users = []
        users = [pwd.getpwnam(user)] if user else pwd.getpwall()
        for user_sys in users:
            path = '/User/{}'.format(user_sys.pw_uid)
            if path not in objects:
                user_obj = User(system_bus, path).load(user_sys.pw_uid)
                objects[path] = user_obj
            ret_users.append(path)
        return ret_users

    def load_user_groups(self, users):
        """ Load the users primary group"""
        for userpath in users:
            grouppath = self.FindGroupById(objects[userpath].GetGID())
            objects[grouppath].main_users.add(userpath)

    def load_group_members(self, groups):
        """ Load all groups and their members """
        for grouppath in groups:
            gr_sys = grp.getgrgid(objects[grouppath].gid)
            for mem in gr_sys.gr_mem:
                objects[grouppath].users.add(self.FindUserByName(mem))
            for userpath in objects[grouppath].users:
                objects[userpath].groups.add(grouppath)

    def reload_groups(self):
        """ Reload all the group members """
        self.load_group_members(self.ListGroups())
        self.load_user_groups(self.ListUsers())

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='sa{sv}', out_signature='o', sender_keyword='sender')
    def CreateUser(self, user_name, other, sender):
        """ Create a system user with the username provided.
            additional Arguments in other are:
                other = {"home": "/home/username",
                         "fullname": "Name of the User",
                         "uid": 1101,
                         "gid": 1101}
                         """
        authorize(sender, errormessage="the user was not created!")
        cmd = ["useradd"]
        if "home" in other:
            cmd.extend(['-m', '-d', other["home"]])
        if "fullname" in other:
            cmd.extend(['-c', other["fullname"]])
        if "uid" in other:
            cmd.extend(['-u', other["uid"]])
        if "gid" in other:
            cmd.extend(['-g', other["gid"]])

        cmd.append(user_name)
        res = common.run_command(cmd)
        if res[0]:
            self.load_groups(user_name)
            self.load_users(user_name)
            self.reload_groups()
            self.on_users_changed()
            return self.FindUserByName(user_name)
        raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='sss', out_signature='o', sender_keyword='sender')
    def CreateUserDetailed(self, user_name, home, fullname, sender):
        self.CreateUser(user_name, {'home': home, 'fullname': fullname}, sender)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='ib', out_signature='b', sender_keyword='sender')
    def DeleteUser(self, uid, remove_files, sender):
        authorize(sender, errormessage="the user was not deleted!")
        path = self.FindUserById(uid)
        if path not in objects:
            raise UserException("A user with the given uid {} was not found".format(uid))
        return objects[path].DeleteUser(remove_files)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='o')
    def FindUserById(self, uid):
        path = '/User/{}'.format(uid)
        return path

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def FindUserByName(self, username):
        try:
            usr = pwd.getpwnam(username)
            return self.FindUserById(usr.pw_uid)
        except KeyError:
            return ''

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListUsers(self):
        return [objects[u].path for u in objects if u.startswith("/User/")]

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o', sender_keyword='sender')
    def CreateGroup(self, group_name, sender):
        # TODO - not working!
        authorize(sender, errormessage="the group was not created!")
        res = common.run_command(['groupadd', group_name])
        if res[0]:
            path = self.FindGroupByName(group_name)
            self.load_groups(group=group_name)
            self.reload_groups()
            self.on_groups_changed()
            return path
        raise GroupException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='b', sender_keyword='sender')
    def DeleteGroup(self, gid, sender):
        authorize(sender, errormessage="the group was not deleted!")
        path = self.FindGroupById(gid)
        if path not in objects:
            raise GroupException("A group with the given gid {} was not found".format(gid))
        return objects[path].DeleteGroup()

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListGroups(self):
        return [objects[u].path for u in objects if u.startswith("/Group/")]

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='s')
    def FindGroupById(self, gid):
        path = "/Group/{}".format(gid)
        return path

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def FindGroupByName(self, group_name):
        group = grp.getgrnam(group_name)
        path = self.FindGroupById(group.gr_gid)
        return path

    @dbus.service.signal(dbus_interface='io.github.ltsp.manager.AccountManager', signature='')
    def on_users_changed(self):
        # print("some user(s) have changed")
        pass

    @dbus.service.signal(dbus_interface='io.github.ltsp.manager.AccountManager', signature='')
    def on_groups_changed(self):
        # print("Some Group(s) have changed")
        pass

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def Version(self):
        return str(version.__version__)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='u', out_signature='bb')
    def IsGIDValidAndFree(self, gid):
        res_valid = not(gid < FIRST_GID or gid > LAST_GID)
        res_free = "/Group/{}".format(gid) not in objects
        return res_valid, res_free

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='bb')
    def IsGroupNameValidAndFree(self, group_name):
        res_free = True
        res_valid = not re.match(NAME_REGEX, group_name)
        res_free = True
        for group in self.ListGroups():
            if objects[group].group_name == group_name:
                res_free = False
        return res_valid, res_free

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='u', out_signature='bb')
    def IsUIDValidAndFree(self, uid):
        res_valid = not(uid < FIRST_UID or uid > LAST_UID)
        res_free = "/User/{}".format(uid) not in objects
        return res_valid, res_free

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='bb')
    def IsUsernameValidAndFree(self, username):
        res_valid = re.match(NAME_REGEX, username)
        res_free = True
        for user in self.ListUsers():
            if objects[user].name == username:
                res_free = False
        return res_valid, res_free

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='o', out_signature='o')
    def LoadByPath(self, path):
        if path in objects:
            return objects[path]
        if path.startswith("/User/"):
            user_id = int(path[6:])
            npath = self.FindUserById(user_id)
            if path == npath:
                return objects[path]
            raise UserException("Usererror")
        if path.startswith("/Group/"):
            group_id = int(path[7:])
            npath = self.FindGroupById(group_id)
            if path == npath:
                return objects[path]
            raise GroupException("Grouperror")


class User(dbus.service.Object):
    """ A usero object for DBUS """

    def load(self, uid):
        usr = pwd.getpwuid(uid)

        self.name = usr.pw_name
        self.uid = uid
        self.path = "/User/{}".format(self.uid)
        self.gid = usr.pw_gid
        self.directory = usr.pw_dir
        self.shell = usr.pw_shell
        self.SUPPORTS_MULTIPLE_CONNECTIONS = True
        self.SUPPORTS_MULTIPLE_OBJECT_PATHS = True
        gecos = usr.pw_gecos.split(',')
        gecos = gecos + ['']*(5-len(gecos))
        self.rname, self.office, self.wphone, self.hphone, self.other = gecos
        self.lstchg, self.min, self.max, self.warn, self.inact, self.expire = [0]*6
        self.groups = set()

        return self

    def remove_groups(self):
        # remove from groups
        for group in self.groups:
            objects[group].users.discard(self.path)
        # remove main group
        main_group = objects[self.GetMainGroup()]
        main_group.main_users.discard(self.path)
        # delete the main group (is automagically done)
        if not (len(main_group.users) or len(main_group.main_users)):
            main_group.remove_from_connection()
            del objects[main_group.path]

        account_manager.on_users_changed()

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='isssssssssiiiiii')
    def GetValues(self):
        # uid, name, primary_group, rname, office, wphone, hphone, other, directory, shell, lstchg, min, max, warn, inact, expire

        return self.uid, self.name, grp.getgrgid(self.gid).gr_name, self.rname, self.office, self.wphone,\
               self.hphone, self.other, self.directory, self.shell, self.lstchg, self.min, self.max, self.warn,\
               self.inact, self.expire

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetUsername(self):
        return str(self.name)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='', sender_keyword='sender')
    def SetUsername(self, user_name, sender):
        authorize(sender, errormessage="the username was not set!")
        cmd = ['usermod']
        cmd.extend(['-l', user_name])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            self.name = user_name
            account_manager.on_users_changed()
            return
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='i')
    def GetUID(self):
        return self.uid

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='s', sender_keyword='sender')
    def SetUID(self, newUID, sender):
        authorize(sender, errormessage="the UID was not set!")
        oldid = self.uid
        cmd = ['usermod']
        cmd.extend(['-u', newUID])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            # Remove the old group_paths
            self.remove_groups()
            self.load(newUID)
            self.groups = set()
            account_manager.reload_groups()
            oldpath = '/User/{}'.format(oldid)
            newpath = '/User/{}'.format(newUID)
            del objects[oldpath]
            objects[newpath] = self
            self.remove_from_connection(system_bus, oldpath)
            self.add_to_connection(system_bus, newpath)
            self.uid = newUID
            account_manager.on_users_changed()
            return newpath
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='i')
    def GetGID(self):
        return self.gid

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='i', sender_keyword='sender')
    def SetGID(self, newGID, sender):
        authorize(sender, errormessage="the GID was not set!")
        cmd = ['usermod']
        cmd.extend(['-g', newGID])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            objects[self.GetMainGroup()].main_users.discard(self.path)
            self.load(self.uid)
            objects[self.GetMainGroup()].main_users.add(self.path)
            account_manager.on_users_changed()
            return self.gid
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='sssss')
    def GetGecos(self):
        return self.rname, self.office, self.wphone, self.hphone, self.other

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetRealName(self):
        return str(self.rname)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetOffice(self):
        return str(self.office)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetWorkPhone(self):
        return str(self.wphone)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetHomePhone(self):
        return str(self.hphone)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetComment(self):
        return str(self.other)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetHomeDir(self):
        return str(self.directory)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetShell(self):
        return str(self.shell)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='b', out_signature='b', sender_keyword='sender')
    def DeleteUser(self, removeFiles, sender):
        authorize(sender, errormessage="the user was not deleted!")
        cmd = ['userdel']
        if removeFiles:
            cmd.append('-r')
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            self.remove_groups()
            # remove from dbus
            self.remove_from_connection()
            # remove objects
            del objects[self.path]
            account_manager.on_users_changed()
            return True
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='b')
    def IsSystemUser(self):
        return not (self.uid >= FIRST_UID and self.uid <= LAST_UID)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='as', out_signature='b')
    def IsPartOfGroups(self, groups):
        mg = self.GetGroups() + (self.GetMainGroup(),)
        if not mg:
            return False
        for g in groups:
            if not g.startswith("/Group/"):
                g = "/Group/"+g
            if mg and (g in mg):
                return True
        return False

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def GetGroups(self):
        # Returns the users Groups. The first group is the users main group, the rest are the supplementary groups.
        return tuple(self.groups)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='o')
    def GetMainGroup(self):
        return "/Group/{}".format(self.gid)

    def get_ids_from_home(self, base='/home'):
        """Returns the owner's UID and GID of the /home/<username>
        if this exists or None.
        """
        path = os.path.join(base, self.name)
        if os.path.isdir(path):
            stat = os.stat(path)
            return [stat.st_uid, stat.st_gid]
        return None


class Group(dbus.service.Object):
    def __init__(self, *args):
        super().__init__(*args)
        self.SUPPORTS_MULTIPLE_CONNECTIONS = True
        self.SUPPORTS_MULTIPLE_OBJECT_PATHS = True

    def load(self, gid):
        group = grp.getgrgid(gid)
        self.group_name = group.gr_name
        self.gid = group.gr_gid
        self.path = "/Group/{}".format(self.gid)

        self.users = set()
        self.main_users = set()
        return self

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='is')
    def GetValues(self):
        return self.gid, self.group_name

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='is', out_signature='u')
    def SetValues(self, new_gid, new_name):
        """ Changes the Group and returns a number of what was changed.
            0 Nothing, 1 Name, 2 GID, 3 Both
            """
        retu = 0
        if self.group_name != new_name:
            self.SetGroupName(new_name)
            retu += 1
        if self.gid != new_gid:
            self.SetGID(new_gid)
            retu += 2
        return retu

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='s')
    def GetGroupName(self):
        return self.group_name

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='s', out_signature='')
    def SetGroupName(self, new_group_name):
        """ Set the GID of this group and adjust the members correctly.
            Return 1 if something has changed and 0 if not."""
        if self.group_name == new_group_name:
            return 0
        res = common.run_command(['groupmod', '-n', new_group_name, self.group_name])
        if res[0]:
            self.group_name = new_group_name
            return 1
        account_manager.on_groups_changed()
        raise GroupException(res[1])

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='u')
    def GetGID(self):
        return self.gid

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='u', out_signature='u')
    def SetGID(self, new_gid):
        """ Set the GID of this group and adjust the members correctly.
            Return 1 if something has changed and 0 if not."""
        if self.gid == new_gid:
            return 0
        res = common.run_command(['groupmod', '-g', str(new_gid), self.group_name])
        if res[0]:
            old_path = self.path
            # print(list(self.locations))
            connection, _dummy, _dummy2 = next(self.locations)
            self.remove_from_connection()
            del objects[self.path]
            self.gid = new_gid
            self.path = "/Group/{}".format(self.gid)
            self.add_to_connection(connection, self.path)
            for x in self.users:
                objects[x].groups.remove(old_path)
                objects[x].groups.add(self.path)
            for x in self.main_users:
                objects[x].gid = self.gid
            account_manager.on_groups_changed()
            return 1
        raise GroupException(res[1])

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='ao')
    def GetUsers(self):
        """ Returns all the users who have this group as supplementary group """
        return self.users

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='ao')
    def GetMainUsers(self):
        """ Retruns the users who have this group as main group """
        return self.main_users

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='o', out_signature='b', sender_keyword='sender')
    def AddUser(self, path, sender):
        authorize(sender, errormessage="the user was not added!")
        user = account_manager.LoadByPath(path)
        res = common.run_command(['gpasswd', '-a', user.name, self.group_name])
        if res[0]:
            user.groups.add(self.path)
            self.users.add(user.path)
            account_manager.on_groups_changed()
            return True
        raise UserException("User does not exist.")

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b')
    def IsPrivateGroup(self):
        return (not self.IsSystemGroup()) and (not self.users)

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b')
    def IsSystemGroup(self):
        return self.gid < FIRST_GID or self.gid > LAST_GID

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='o', out_signature='b', sender_keyword='sender')
    def RemoveUser(self, path, sender):
        authorize(sender, errormessage="the user was not removed!")
        if path in self.users:
            user = account_manager.LoadByPath(path)
            res = common.run_command(['gpasswd', '-d', user.name, self.group_name])
            if res[0]:
                self.users.discard(user.path)
                user.groups.discard(self.path)
                account_manager.on_groups_changed()
                return True
            raise UserException("Failed to remove user.")
        raise UserException("User not in this group.")

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b', sender_keyword='sender')
    def DeleteGroup(self, sender):
        authorize(sender, errormessage="the group was not deleted!")
        if self.main_users:
            raise GroupException("There are users that have this group as their main group - {}".format(','.join(self.main_users)))
        res = common.run_command(['groupdel', self.group_name])
        if res[0]:
            # remove the group from all its users
            for user_path in self.users:
                objects[user_path].groups.discard(self.path)
            # remove the group from dbus
            for x in self.locations:
                del objects[x[1]]
            self.remove_from_connection()
            account_manager.on_groups_changed()
            return True
        raise GroupException(res[1])


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    system_bus = dbus.SystemBus()

    name = dbus.service.BusName("io.github.ltsp-manager", system_bus)
    system_bus_name = system_bus.get_unique_name()
    print(name, system_bus_name)
    account_manager = AccountManager(system_bus, '/AccountManager')
    proxy = system_bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
    polkit = dbus.Interface(proxy, dbus_interface='org.freedesktop.PolicyKit1.Authority')
    mainloop = GLib.MainLoop()
    print("Starting Gum user manager")
    mainloop.run()
