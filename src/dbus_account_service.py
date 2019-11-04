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
import paths
import iso843

objects = {#path:object
}


FIRST_SYSTEM_UID=0
LAST_SYSTEM_UID=999

FIRST_SYSTEM_GID=0
LAST_SYSTEM_GID=999

FIRST_UID=1000
LAST_UID=29999

FIRST_GID=1000
LAST_GID=29999

class DBusClass():
    def __init__(self):
        path = os.path.join(paths.pkgdatadir, 'dbus', type(self).__name__ + '.xml')
        with open(path) as f:
            self.doc = f.read()

class UserException(dbus.DBusException):
     _dbus_error_name = 'io.github.ltsp.manager.UserException'
class GroupException(dbus.DBusException):
     _dbus_error_name = 'io.github.ltsp.manager.GroupException'

class AccountManager(dbus.service.Object):
    def __init__(self, *args):
        super().__init__(*args)

    def _filter_(self, prefix):
        ret = []
        for key in objects:
            if key.startswith(prefix):
                ret.append(key)
        return ret

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='sa{ss}', out_signature='o')
    def CreateUser(self, name, other):
        cmd = ["useradd"]
        if "home" in other:
            cmd.extend(['-m', '-d', other["home"]])
        if "fullname" in other:
            cmd.extend(['-c', other["fullname"]])
        cmd.append(name)
        res = common.run_command(cmd)
        if res[0]:
            return self.FindUserByName(name)
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='ib', out_signature='b')
    def DeleteUser(self, uid, removeFiles):
        try:
            path = self.FindUserById(uid)
        except:
            raise UserException("A user with the given uid {} was not found".format(uid))
        return objects[path].DeleteUser(removeFiles)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='o')
    def FindUserById(self, uid):
        path = '/User/{}'.format(uid)
        if not path in objects:
            user = User(system_bus, path).LoadUID(uid)
            objects[path] = user

        return path

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def FindUserByName(self, username):
        usr = pwd.getpwnam(username)
        return self.FindUserById(usr.pw_uid)


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListCachedUsers(self):
        return self._filter_("/User/")

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListUsers(self):
        users = []
        for user in pwd.getpwall():
            path = "/User/{}".format(user.pw_uid)
            if not path in objects:
                user = User(system_bus, path).LoadUID(user.pw_uid)
                objects[path] = user
            users.append(path)
        return users

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def CreateGroup(self, groupname):
        res = common.run_command(['groupadd', groupname])
        if res[0]:
            path = self.FindGroupByName(groupname)
            return path
        else:
            raise GroupException(res[1])


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='b')
    def DeleteGroup(self, gid):
        try:
            path = self.FindGroupById(gid)
        except:
            raise GroupException("A group with the given gid {} was not found".format(gid))
        return objects[path].DeleteGroup()


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListCachedGroups(self):
        return self._filter_("/Group/")


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def ListGroups(self):
        groups = []
        for group in grp.getgrall():
            path = "/Group/{}".format(group.gr_gid)
            if not path in objects:
                group = Group(system_bus, path).LoadGID(group.gr_gid)
                objects[path] = group
            groups.append(path)
        return groups


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='s')
    def FindGroupById(self, gid):
        path = "/Group/{}".format(gid)
        if not path in objects:
            group = Group(system_bus, path).LoadGID(gid)
            objects[path] = group
        return path

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='o')
    def FindGroupByName(self, groupname):
        group = grp.getgrnam(groupname)
        path = self.FindGroupById(group.gr_gid)
        return path

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

    def LoadUID(self, uid):
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


    def create(self, name=None,\
                 uid=None, gid=None, rname="", office="",
                 wphone="", hphone="", other="",
                 directory=None, shell="/bin/bash",
                 groups=None, lstchg=None,
                 min=0, max=99999, warn=7, inact=-1,
                 expire=-1, password="*", plainpw=None, *args):
        super().__init__(*args)

        self.name, self.uid, self.gid, self.rname = name, uid, gid, rname
        self.office, self.wphone, self.hphone = office, wphone, hphone
        self.other, self.directory, self.shell = other, directory, shell
        self.groups, self.lstchg, self.min = groups, lstchg, min
        self.max, self.warn, self.inact = max, warn, inact
        self.expire, self.password, self.plainpw = expire, password, plainpw


        if not self.name and self.rname:
            self.name = iso843.transcript(rname)

        if self.groups is None:
            self.groups = []

        if self.gid is not None:
            try:
                self.primary_group = grp.getgrgid(self.gid).gr_name
            except:
                self.primary_group = ''
        else:
            self.primary_group = None

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='s')
    def GetUsername(self):
        return str(self.name)

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='s', out_signature='')
    def SetUsername(self, name):
        cmd = ['usermod']
        cmd.extend(['-l', name])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            self.name = name
            return
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='i')
    def GetUID(self):
        print(self.uid)
        return self.uid

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='s')
    def SetUID(self, newUID):
        oldid = self.uid
        print(oldid, self.uid)
        cmd = ['usermod']
        cmd.extend(['-u', newUID])
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            self.LoadUID(newUID)
            oldpath = '/User/{}'.format(oldid)
            newpath = '/User/{}'.format(newUID)
            print(oldpath, newpath)
            del objects[oldpath]
            objects[newpath] = self
            self.remove_from_connection(system_bus, oldpath)
            self.add_to_connection(system_bus, newpath)
            self.uid = newUID
            return newpath
        else:
            raise UserException(res[1])

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='i')
    def GetGID(self):
        print(self.gid)
        return self.gid

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='i', out_signature='i')
    def SetGID(self, newGID):
        cmd = ['usermod']
        cmd.extend(['-g', newGID])
        cmd.append(username)
        res = common.run_command(cmd)
        if res[0]:
            self.LoadUID(self.uid)
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

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='b', out_signature='b')
    def DeleteUser(self, removeFiles):
        cmd = ['userdel']
        if removeFiles:
            cmd.append('-r')
        cmd.append(self.name)
        res = common.run_command(cmd)
        if res[0]:
            for x in self.locations:
                del(objects[x[1]])
            self.remove_from_connection()
            return True
        else:
            raise UserException(res[1])


    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='b')
    def IsSystemUser(self):
        if self.uid:
            return not (self.uid >= FIRST_UID and self.uid <= LAST_UID)
        else:
            return False

    @dbus.service.method("io.github.ltsp.manager.AccountManager", in_signature='', out_signature='ao')
    def GetGroups(self):
        # Returns the users Groups. The first group is the users main group, the rest are the supplementary groups.
        accountManager.ListGroups()
        return ["/Group/{}".format(self.gid)].extend(self.groups)

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

    def LoadGID(self, gid):
        group = grp.getgrgid(gid)
        self.GroupName = group.gr_name
        self.GID = group.gr_gid
        self.path = "/Group/{}".format(self.GID)
        self.Users = [accountManager.FindUserByName(name) for name in group.gr_mem]
        for userpath in self.Users:
            objects[userpath].groups.add(self.path)
        return self

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='s')
    def GetGroupName(self):
        return self.GroupName

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='i')
    def GetGID(self):
        return self.GID

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='ao')
    def GetUsers(self):
        return self.Users

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='o', out_signature='b')
    def AddUser(self, path):
        user = accountManager.LoadByPath(path)
        res = common.run_command(['gpasswd', '-a', user.name, self.GroupName])
        self.LoadGID(self.GID)
        if path in self.Users:
            return True
        else:
            raise UserException("User does not exist.")


    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='o', out_signature='b')
    def RemoveUser(self, path):
        if path in self.Users:
            user = accountManager.LoadByPath(path)
            res = common.run_command(['gpasswd', '-d', user.name, self.GroupName])
            self.LoadGID(self.GID)
            if not path in self.Users:
                return True
            else:
                raise UserException("Failed to remove user.")
        else:
            raise UserException("User not in this group.")

    @dbus.service.method("io.github.ltsp.manager.Group", in_signature='', out_signature='b')
    def DeleteGroup(self):
        res = common.run_command(['groupdel',  self.GroupName])
        if res[0]:
            for x in self.locations:
                del(objects[x[1]])
            self.remove_from_connection()
            return True
        else:
            raise GroupException(res[1])







if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    system_bus = dbus.SystemBus()

    name = dbus.service.BusName("io.github.ltsp-manager", system_bus)
    accountManager = AccountManager(system_bus, '/AccountManager')

    mainloop = GLib.MainLoop()
    print("Starting Gum user manager")
    mainloop.run()
