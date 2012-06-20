#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import os
import shlex
import stat
import sys
import subprocess
import libuser

# TODO: after the workshop, let's move the shared_folders ui into its own
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
        contents=shlex.split(open("/etc/default/shared-folders").read(), True)
        self.config.update(dict(v.split("=") for v in contents))
        self.config["SHARE_DIR/"]=os.path.join(self.config["SHARE_DIR"], "")
        self.config["SHARE_CONF"]=self.config["SHARE_DIR/"] + ".shared-folders"
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
        self.ensure_dir(self.config["SHARE_DIR"], 0711,
            adm_uid, int(self.config["ADM_GID"]))
        self.ensure_dir(self.config["SHARE_DIR/"] + ".symlinks", 0731,
            adm_uid, self.system.groups[self.config["TEACHERS"]].gid)
        for group in groups:
            dir=self.config["SHARE_DIR/"] + group
            group_gid=self.system.groups[group].gid
            self.ensure_dir(dir, 0770, adm_uid, group_gid)
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
        for line in file("/proc/mounts").readlines():
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
        """Save share_groups to /home/Shared/.shared-folders."""
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

def usage():
    return """Χρήση: shared-folders [ΕΝΤΟΛΕΣ]

Διαχειρίζεται κοινόχρηστους φακέλους για συγκεκριμένες ομάδες χρηστών,
με τη βοήθεια του bindfs.

Εντολές:
    add <ομάδες>
        Δημιουργεί φακέλους για τις καθορισμένες ομάδες, εάν δεν υπάρχουν
        ήδη, και τους προσαρτεί με χρήση του bindfs.
    list-mounted <ομάδες>
        Εμφανίζει ποιες από τις καθορισμένες ομάδες έχουν προσαρτημένους
        φακέλους.
    list-shared <ομάδες>
        Εμφανίζει ποιες από τις καθορισμένες ομάδες έχουν ενεργοποιημένους
        τους κοινόχρηστους φακέλους.
    mount <ομάδες>
        Επαναπροσαρτεί τους κοινόχρηστους φακέλους για όσες από τις
        καθορισμένες ομάδες έχει αλλάξει το όνομα ή το GID, και για όσες
        δεν ήταν προσαρτημένοι οι φάκελοί τους.
    rename <παλιά ομάδα> <νέα ομάδα>
        Αλλάζει το όνομα ενός φακέλου από την παλιά του ομάδα στη νέα,
        η οποία πρέπει είναι υπαρκτή. Εάν ο φάκελος ήταν προσαρτημένος,
        αποπροσαρτείται, μετονομάζεται και προσαρτείται πάλι.
    remove <ομάδες>
        Αποπροσαρτεί και αφαιρεί τη δυνατότητα κοινόχρηστων φακέλων από
        τις καθορισμένες ομάδες. Οι φάκελοι δεν διαγράφονται από το
        σύστημα αρχείων.
    unmount <ομάδες>
        Αποπροσαρτεί τους κοινόχρηστους φακέλους των καθορισμένων ομάδων.

Σε όλες τις παραπάνω περιπτώσεις εκτός από την add και τη rename, εάν δεν
καθοριστούν οι <ομάδες>, χρησιμοποιούνται όλες οι κοινόχρηστες ομάδες.
"""

if __name__ == '__main__':
    if (len(sys.argv) <= 1) or (len(sys.argv) == 2
      and (sys.argv[1] == '-h' or sys.argv[1] == '--help')):
        print usage()
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
        print ' '.join(sf.list_mounted(groups))
    elif cmd == "list-shared":
        print ' '.join(sf.list_shared(groups))
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
