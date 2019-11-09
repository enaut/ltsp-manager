#!/usr/bin/env python3

# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

from gi.repository import GLib

import dbus
import dbus.service
import dbus.mainloop.glib
import os

import grp
import pwd

import common
import version

objects = {# will be populated with: dbus-path:object
}


FIRST_SYSTEM_UID=0
LAST_SYSTEM_UID=999

FIRST_SYSTEM_GID=0
LAST_SYSTEM_GID=999

FIRST_UID=1000
LAST_UID=29999

FIRST_GID=1000
LAST_GID=29999

class UserException(dbus.DBusException):
     _dbus_error_name = 'io.github.ltsp.manager.UserException'
class GroupException(dbus.DBusException):
     _dbus_error_name = 'io.github.ltsp.manager.GroupException'
class PermissionDeniedException(dbus.DBusException):
     _dbus_error_name = 'io.github.ltsp.manager.PermissionDeniedException'


def authorize(sender, errormessage):
    # Check Authorization with following parameters in d-feet:
    # ('system-bus-name', {'name' :  GLib.Variant("s",':1.13424')}), 'io.github.ltsp-manager.accountmanager.createuser', {}, 1, ''
    subject = ('system-bus-name', {'name': sender})
    action_id = "io.github.ltsp-manager.accountmanager"
    details = {}
    flags = 1
    cancellation_id = ''
    auth = polkit.CheckAuthorization(subject, action_id, details, flags, cancellation_id)
    if not auth[0]:
        print("Authentication not granted: ", errormessage, auth)
        print(auth[0])
        raise PermissionDeniedException("Authentication was not possible: {}".format(errormessage))
    return auth

class AccountManager(dbus.service.Object):
    def __init__(self, *args):
        super().__init__(*args)
        users = self.load_users()
        groups = self.load_groups()
        self.load_group_members(groups)
        self.load_user_groups(users)
        self.on_users_changed()

    def _filter_(self, prefix):
        ret = []
        for key in objects:
            if key.startswith(prefix):
                ret.append(key)
        return ret


    def load_groups(self, group = None):
        ret_groups = []
        groups = [grp.getgrnam(group)] if group else grp.getgrall()
        for group in groups:
            path = "/Group/{}".format(group.gr_gid)
            if not path in objects:
                group = Group(system_bus, path).load_gid(group.gr_gid)
                objects[path] = group
            ret_groups.append(path)
        return ret_groups

    def load_users(self, user=None):
        ret_users = []
        users = [pwd.getpwnam(user)] if user else pwd.getpwall()
        for user in users:
            path = '/User/{}'.format(user.pw_uid)
            if not path in objects:
                user = User(system_bus, path).load_uid(user.pw_uid)
                objects[path] = user
            ret_users.append(path)
        return ret_users

    def load_user_groups(self, users):
        """Needs to be called after LoadGroupMembers"""
        for userpath in users:
            grouppath = self.FindGroupById(objects[userpath].GetGID())
            objects[grouppath].main_users.add(userpath)

    def load_group_members(self, groups):
        for grouppath in groups:
            gr = grp.getgrgid(objects[grouppath].gid)
            for mem in gr.gr_mem:
                objects[grouppath].users.add(self.FindUserByName(mem))
            for userpath in objects[grouppath].users:
                objects[userpath].groups.add(grouppath)

    def reload_groups(self):
        self.load_group_members(self.ListGroups())
        self.load_user_groups(self.ListUsers())

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='sa{ss}', out_signature='o', sender_keyword='sender')
    def CreateUser(self, name, other, sender):
        authorize(sender, errormessage="the user was not created!")
        cmd = ["useradd"]
        if "home" in other:
            cmd.extend(['-m', '-d', other["home"]])
        if "fullname" in other:
            cmd.extend(['-c', other["fullname"]])
        cmd.append(name)
        res = common.run_command(cmd)
        if res[0]:
            self.load_groups(name)
            self.load_users(name)
            self.reload_groups()
            self.on_users_changed()
            return self.FindUserByName(name)
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='ib', out_signature='b', sender_keyword='sender')
    def DeleteUser(self, uid, removeFiles, sender):
        authorize(sender, errormessage="the user was not deleted!")
        try:
            path = self.FindUserById(uid)
        except:
            raise UserException("A user with the given uid {} was not found".format(uid))

        return objects[path].DeleteUser(removeFiles)

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
        return [ objects[u].path for u in objects if u.startswith("/User/")]

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o', sender_keyword='sender')
    def CreateGroup(self, groupname, sender):
        # TODO - not working!
        authorize(sender, errormessage="the group was not created!")
        res = common.run_command(['groupadd', groupname])
        if res[0]:
            path = self.FindGroupByName(groupname)
            self.on_groups_changed()
            return path
        else:
            raise GroupException(res[1])


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='b', sender_keyword='sender')
    def DeleteGroup(self, gid, sender):
        authorize(sender, errormessage="the group was not deleted!")
        try:
            path = self.FindGroupById(gid)
        except:
            raise GroupException("A group with the given gid {} was not found".format(gid))
        return objects[path].DeleteGroup()


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListGroups(self):
        return [ objects[u].path for u in objects if u.startswith("/Group/")]

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='s')
    def FindGroupById(self, gid):
        path = "/Group/{}".format(gid)
        return path

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def FindGroupByName(self, groupname):
        group = grp.getgrnam(groupname)
        path = self.FindGroupById(group.gr_gid)
        return path

    @dbus.service.signal(dbus_interface='io.github.ltsp.manager.AccountManager', signature='')
    def on_users_changed(self):
        pass

    @dbus.service.signal(dbus_interface='io.github.ltsp.manager.AccountManager', signature='')
    def on_groups_changed(self):
        pass


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='')
    def Exit(self):
        mainloop.quit()

    #UserAdded = dbus.generic.signal()
    #UserDeleted = dbus.generic.signal()

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def Version(self):
        return str(version.__version__)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='o', out_signature='o')
    def LoadByPath(self, path):
        if path in objects:
            return objects[path]
        else:
            if path.startswith("/User/"):
                id = int(path[6:])
                npath = self.FindUserById(id)
                if path == npath:
                    return objects[path]
                else:
                    raise UserException("Usererror")
                return objects[path]
            if path.startswith("/Group/"):
                id = int(path[7:])
                npath = self.FindGroupById(id)
                if path == npath:
                    return objects[path]
                else:
                    raise GroupException("Grouperror")



class User(dbus.service.Object):

    def load_uid(self, uid):
        usr = pwd.getpwuid(uid)

        self.name = usr.pw_name
        self.uid = uid
        self.path = "/User/{}".format(self.uid)
        self.gid = usr.pw_gid
        self.rname = usr.pw_gecos
        self.directory = usr.pw_dir
        self.shell = usr.pw_shell
        self.SUPPORTS_MULTIPLE_CONNECTIONS = True
        self.SUPPORTS_MULTIPLE_OBJECT_PATHS = True
        self.groups = set()

        return self

    def remove_groups(self, sender):
        # remove from groups
        for gr in self.groups:
            objects[gr].users.discard(self.path)
        # remove main group
        mg = objects[self.GetMainGroup()]
        mg.main_users.discard(self.path)
        # delete the main group (is automagically done)
        if not (len(mg.users) or len(mg.main_users)):
             mg.remove_from_connection()
             del objects[mg.path]

        account_manager.on_users_changed()

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='isssssssssiiiiii')
    def GetValues(self):
        # uid, name, primary_group, rname, office, wphone, hphone, other, directory, shell, lstchg, min, max, warn, inact, expire
        self.office, self.wphone, self.hphone, self.other = ['']*4
        self.lstchg, self.min, self.max, self.warn, self.inact, self.expire = [0]*6

        return self.uid, self.name, grp.getgrgid(self.gid).gr_name, self.rname, self.office, self.wphone, self.hphone, self.other, self.directory, self.shell, self.lstchg, self.min, self.max, self.warn, self.inact, self.expire

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetUsername(self):
        return str(self.name)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='', sender_keyword='sender')
    def SetUsername(self, name, sender):
        authorize(sender, errormessage="the username was not set!")
        cmd = ['usermod']
        cmd.extend(['-l', name])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            self.name = name
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
            self.remove_groups(sender)
            self.load_uid(newUID)
            self.groups=set()
            account_manager.ReloadGroups()
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
            self.load_uid(self.uid)
            objects[self.GetMainGroup()].main_users.add(self.path)
            account_manager.on_users_changed()
            return self.gid
        else:
            raise UserException(res[1])

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
            self.remove_groups(sender)
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
        mg =  self.GetGroups() + (self.GetMainGroup(),)
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
        if os.isdir(path):
            stat = os.stat(path)
            return [stat.st_uid, stat.st_gid]
        return None

    #Changed = dbus.generic.signal()

class Group(dbus.service.Object):
    def __init__(self, *args):
        super().__init__(*args)

    def load_gid(self, gid):
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

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='s')
    def GetGroupName(self):
        return self.group_name

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='i')
    def GetGID(self):
        return self.gid

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
            return True
        else:
            raise UserException("User does not exist.")

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b')
    def IsPrivateGroup(self):
        return (not self.IsSystemGroup()) and  (not self.users)

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
            else:
                raise UserException("Failed to remove user.")
        else:
            raise UserException("User not in this group.")

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b', sender_keyword='sender')
    def DeleteGroup(self, sender):
        authorize(sender, errormessage="the group was not deleted!")
        if self.main_users:
            raise GroupException("There are users that have this group as their main group - {}".format(','.join(self.main_users)))
        res = common.run_command(['groupdel',  self.group_name])
        if res[0]:
            # remove the group from all its users
            for us in self.users:
                objects[us].groups.discard(self.path)
            # remove the group from dbus
            for x in self.locations:
                del(objects[x[1]])
            self.remove_from_connection()
            account_manager.on_groups_changed()
            return True
        else:
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
