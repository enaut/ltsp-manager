#!/usr/bin/env python3

# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

import os
import shlex
import stat
import sys
import subprocess
import libuser
import version

# TODO: after the workshop, let's move the ltsp_shared_folders ui into its own
# dialog, and only disable editing groups that have shares in group_form.py
# Unrelated, we might also want a "restrict_dirs" function that
# chrgrp's the user dirs to "teachers".

class SharedFolders():
    def __init__(self, system=None):
        """Initialization."""
        if system is None:
            self.system=libuser.System()
        else:
            self.system=system
        self.load_config()

    def add(self, groups):
        """Add the specified groups to share_groups, and mount them."""
        groups=self.valid(groups)
        self.system.share_groups=list(set(self.system.share_groups + groups))
        self.mount(groups)
        self.save_config()

    def ensure_dir(self, dir, mode, uid=-1, gid=-1):
        """Ensures that dir exists with the specified mode, uid and gid."""
        if not os.path.isdir(dir):
            os.mkdir(dir)
        s=os.stat(dir)
        m=stat.S_IMODE(s.st_mode)
        if m != mode:
            os.chmod(dir, mode)
        if (uid != -1 and uid != s.st_uid) or (gid != -1 and gid != s.st_gid):
            os.chown(dir, uid, gid)

    def list_mounted(self, groups=None):
        """Return which of the specified groups are mounted."""
        groups=self.valid(groups)
        mounted=[]
        for mount in self.parse_mounts():
            if mount['group'] in groups:
                mounted.append(mount['group'])
        return mounted

    def list_shared(self, groups=None):
        """Return which of the specified groups are shared."""
        groups=self.valid(groups)
        return self.valid(list(set(self.system.share_groups) & set(groups)))

    def load_config(self):
        """Read the shell configuration files."""
        # Start with default values for self.config, and then update them.
        self.config={
            "DISABLE_SHARED_FOLDERS":"false",
            "RESTRICT_DIRS":"true",
            "TEACHERS":"teachers",
            "SHARE_DIR":"/home/Shared",
            "SHARE_GROUPS":"teachers",
            "ADM_UID":"1000",
            "ADM_GID":"1000"}
        contents=shlex.split(open(paths.sysconfdir + "/default/ltsp-shared-folders").read(), True)
        self.config.update(dict(v.split("=") for v in contents))
        self.config["SHARE_DIR/"]=os.path.join(self.config["SHARE_DIR"], "")
        self.config["SHARE_CONF"]=self.config["SHARE_DIR/"] + ".ltsp-shared-folders"
        if os.path.isfile(self.config['SHARE_CONF']):
            contents=shlex.split(open(self.config['SHARE_CONF']).read(), True)
            self.config.update(dict(v.split("=") for v in contents))
        self.system.teachers=self.config["TEACHERS"]
        self.system.share_groups=self.config["SHARE_GROUPS"].split(" ")

    def mount(self, groups=None):
        """Mount or remount the folders for the specified groups."""
        groups=self.valid(groups)
        # Remove from groups the ones that don't need to be (re)mounted.
        # Unmount the ones that need remounting, without removing them.
        for mount in self.parse_mounts():
            group=mount["group"]
            if group not in groups:
                continue
            if self.system.groups[group].gid == mount["gid"]:
                groups.remove(group)
            else:
                self.unmount(group)
        # Then mount what's left.
        # This might actually be the first time to mount anything,
        # so ensure that all the dirs/symlinks are there.
        adm_uid=int(self.config["ADM_UID"])
        self.ensure_dir(self.config["SHARE_DIR"], 0o711,
            adm_uid, int(self.config["ADM_GID"]))
        self.ensure_dir(self.config["SHARE_DIR/"] + ".symlinks", 0o731,
            adm_uid, self.system.groups[self.config["TEACHERS"]].gid)
        for group in groups:
            dir=self.config["SHARE_DIR/"] + group
            group_gid=self.system.groups[group].gid
            self.ensure_dir(dir, 0o770, adm_uid, group_gid)
            subprocess.call(["bindfs",
                "-u", str(adm_uid),
                "--create-for-user=%s" % adm_uid,
                "-g", str(group_gid),
                "--create-for-group=%s" % group_gid,
                "-p", "770,af-x", "--chown-deny", "--chgrp-deny",
                "--chmod-deny", dir, dir])

    def rename(self, src, dst):
        """Rename folder src to group dst.
           Call groupmod to rename the group before calling this function."""
        if dst not in self.system.groups:
            sys.stderr.write("%s is not a valid group.\n" % dst)
            return
        mounted=self.unmount(src)
        # TODO: check if dst exists etc
        os.rename(src, dst)
        self.system.share_groups=list(
            (set(self.system.share_groups) - set([src])) | set([dst]))
        if mounted is not None:
            self.mount(dst)
        self.save_config()

    def parse_mounts(self):
        """Return a list of all bindfs mounts unset /home/Shared."""
        mounts=[]
        with open("/proc/mounts", "r") as f:
            for line in f.readlines():
                items=line.split()
                if items[0] != "bindfs"  or items[2] != "fuse.bindfs" \
                  or not items[1].startswith(self.config["SHARE_DIR/"]):
                    continue
                mount={}
                mount['point']=items[1]
                mount['group']=mount['point'].partition(
                    self.config["SHARE_DIR/"])[2]
                if mount['group'] not in self.system.share_groups:
                    continue
                stat=os.stat(mount['point'])
                mount['uid']=stat.st_uid
                mount['gid']=stat.st_gid
                mounts.append(mount)
        return mounts

    def remove(self, groups=None):
        """Un-share specified folders and remove them from share_groups."""
        if groups is None or groups == []:
            groups=self.system.share_groups
        self.unmount(groups)
        self.system.share_groups=list(
            set(self.system.share_groups) - set(groups))
        self.save_config()

    def save_config(self):
        """Save share_groups to /home/Shared/.ltsp-shared-folders."""
        f=open(self.config["SHARE_CONF"], "w")
        f.write("""# List of groups for which shared folders will be created.
SHARE_GROUPS="%s"
""" % ' '.join(self.system.share_groups))
        f.close()

    def unmount(self, groups=None):
        """Return the folders that were actually unmounted."""
        if groups is None or groups == []:
            groups=self.system.share_groups
        ret=[]
        for mount in self.parse_mounts():
            group=mount["group"]
            if group not in groups:
                continue
            ret.append(group)
            point=mount["point"]
            if subprocess.call(["umount", point]) == 0:
                continue
            sys.stderr.write("Cannot unmount %s, forcing unmount..." % point)
            subprocess.call(["umount", "-l", point])
        return ret

    def valid(self, groups=None):
        """Return which of the specified groups are defined in /etc/group."""
        if groups is None or groups == []:
            groups=self.system.share_groups
        return list(set(self.system.groups) & set(groups))

def gen_usage():
    return _("""Usage: ltsp-shared-folders [COMMANDS]

Manage shared folders for specific user groups, with the help of bindfs.

COMMANDS
    add <groups>
        Create folders for the specified groups, if they don't already exist,
        and mount them using bindfs.

    list-mounted <groups>
        List which of the specified groups have mounted folders.

    list-shared <groups>
        List which of the specified groups have shared folders.

    mount <groups>
        Remount the shared folders for the specified groups, where the name
        or GID have changed, or where the folders are not already mounted.

    rename <old group> <new group>
        Rename a folder from the old to the new group name, which must already
        exist. If the folder is already mounted, then unmount it, rename it,
        and mount it again.

    remove <groups>
        Unmount and remove the sharing for the specified groups. The folders
        are not removed from the file system.

    unmount <groups>
        Unmount the shared folders for the specified groups.

In all the aforementioend commands, except for add and rename, if no groups are
specified, then the command is applied to all the shared groups.
""")

def gen_version():
    return _("""ltsp-manager %s
Copyright (C) 2009-2017 Alkis Georgopoulos <alkisg@gmail.com>, Fotis Tsamis <ftsamis@gmail.com>.
License GPLv3+: GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>.

Authors: Alkis Georgopoulos <alkisg@gmail.com>, Fotis Tsamis <ftsamis@gmail.com>.""") % version.__version__

if __name__ == '__main__':
    if (len(sys.argv) <= 1) or (len(sys.argv) == 2
      and (sys.argv[1] == '-h' or sys.argv[1] == '--help')):
        print(gen_usage())
        sys.exit(0)
    if (len(sys.argv) <= 1) or (len(sys.argv) == 2
      and (sys.argv[1] == '-v' or sys.argv[1] == '--version')):
        print(gen_version())
        sys.exit(0)
    sf=SharedFolders()
    cmd=sys.argv[1]
    groups=sys.argv[2:]
    if cmd == "add":
        if len(sys.argv) < 3:
            sys.stderr.write(usage() + "\n")
            sys.exit(1)
        sf.add(groups)
    elif cmd == "list-mounted":
        print(' '.join(sf.list_mounted(groups)))
    elif cmd == "list-shared":
        print(' '.join(sf.list_shared(groups)))
    elif cmd == "mount":
        sf.mount(groups)
    elif cmd == "rename":
        if len(sys.argv) != 4:
            sys.stderr.write(usage() + "\n")
            sys.exit(1)
        sf.rename(groups[0], groups[1])
    elif cmd == "remove":
        sf.remove(groups)
    elif cmd == "unmount":
        sf.unmount(groups)
    else:
        sys.stderr.write(usage() + "\n")
        sys.exit(1)
