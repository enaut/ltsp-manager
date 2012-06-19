#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2012 Fotis Tsamis <ftsamis@gmail.com>, Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

import os
import shlex
import sys
import subprocess
import libuser

# TODO: update group_form to match the implemented SharedFolders() interface.
# TODO: we also need a "start" mechanism, to be used on boot.
# See the "start" function of the previous version of the
# debian/shared-folders.init shell script. ensure_dir to make sure that
# /home/Shared and /home/Shared/.symlinks exist and have appropriate
# permissions etc.
# I'll make a wrapper /usr/sbin/shared-folders shell script that calls
# shared_folders.py with the appropriate parameters.
# And for after the workshop, we need a "restrict_dirs" function that
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
        """Add the specified groups to share_groups, and remount them."""
        groups=self.valid(groups)
        self.share_groups=list(set(self.share_groups + groups))
        self.remount(groups)
        self.save_config()

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
        return self.valid(list(set(self.share_groups) & set(groups)))

    def load_config(self):
        """Read the shell configuration files."""
        # Start with default values for self.config, and then update them.
        self.config={
            "DISABLE_SHARED_FOLDERS":"false",
            "RESTRICT_DIRS":"true",
            "TEACHERS":"teachers",
            "SHARE_DIR":"/home/Shared",
            "SHARE_GROUPS":"teachers",
            "ADM_UID":"1000"}
        contents=shlex.split(open("/etc/default/shared-folders").read(), True)
        self.config.update(dict(v.split("=") for v in contents))
        self.config["SHARE_DIR/"]=os.path.join(self.config["SHARE_DIR"], "")
        self.config["SHARE_CONF"]=self.config["SHARE_DIR/"] + ".shared-folders"
        if os.path.isfile(self.config['SHARE_CONF']):
            contents=shlex.split(open(self.config['SHARE_CONF']).read(), True)
            self.config.update(dict(v.split("=") for v in contents))
        self.share_groups=self.config["SHARE_GROUPS"].split(" ")

    def rename(self, src, dst):
        """Rename folder src to group dst.
           Call groupmod to rename the group before calling this function."""
        if dst not in self.system.groups:
            sys.stderr.write("%s is not a valid group.\n" % dst)
            return
        mounted=self.unmount(src)
        # TODO: check if dst exists etc
        os.rename(src, dst)
        self.share_groups=list((set(self.share_groups) - set([src]))
            | set([dst]))
        if mounted is not None:
            self.remount(dst)
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
            if mount['group'] not in self.share_groups:
                continue
            stat=os.stat(mount['point'])
            mount['uid']=stat.st_uid
            mount['gid']=stat.st_gid
            mounts.append(mount)
        return mounts

    def remove(self, groups=None):
        """Un-share specified folders and remove them from share_groups."""
        if groups is None:
            groups=self.share_groups
        self.unmount(groups)
        self.share_groups=list(set(self.share_groups)-set(groups))
        self.save_config()

    def remount(self, groups=None):
        """Mount or remount the folders for the specified groups."""
        groups=self.valid(groups)
        # Remove from groups the ones that don't need to be (re)mounted.
        # Unmount the ones that need remounting, without removing them.
        for mount in self.parse_mounts():
            group=mount["group"]
            if group not in groups:
                continue
            if self.system.groups[group].gid == mount["gid"]:
                groups.delete(group)
            else:
                self.unmount(group)
        # Then mount what's left.
        for group in groups:
            dir=self.config["SHARE_DIR/"] + group
            if not os.path.isdir(dir):
                os.mkdir(dir)
            os.chmod(dir, 0770)
            os.chown(dir, int(self.config["ADM_UID"]),
                self.system.groups[self.config["TEACHERS"]].gid)
            subprocess.call(["bindfs",
                "-u", self.config["ADM_UID"],
                "--create-for-user=%s" % self.config["ADM_UID"],
                "-g", str(self.system.groups[group].gid),
                "--create-for-group=%s" % self.system.groups[group].gid,
                "-p", "770,af-x", "--chown-deny", "--chgrp-deny",
                "--chmod-deny", dir, dir])


    def save_config(self):
        """Save share_groups to /home/Shared/.shared-folders."""
        f=open(self.config["SHARE_CONF"], "w")
        f.write("""# List of groups for which shared folders will be created.
SHARE_GROUPS="%s"
""" % ' '.join(self.share_groups))
        f.close()

    def unmount(self, groups=None):
        """Return the folders that were actually unmounted."""
        if groups is None:
            groups=self.share_groups
        ret=[]
        for mount in self.parse_mounts():
            group=mount["group"]
            if group not in groups:
                continue
            ret.append(group)
            point=mount["point"]
            if subprocess.call(["unmount", point]):
                continue
            sys.stderr.write("Cannot unmount %s, forcing unmount..." % point)
            subprocess.call(["unmount", "-l", point])
        return ret

    def valid(self, groups=None):
        """Return which of the specified groups are defined in /etc/group."""
        if groups is None:
            groups=self.share_groups
        return list(set(self.system.groups) & set(groups))

def usage():
    return """Χρήση: $0 [ΕΝΤΟΛΕΣ]

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
    rename <παλιά ομάδα> <νέα ομάδα>
        Αλλάζει το όνομα ενός φακέλου από την παλιά του ομάδα στη νέα,
        η οποία πρέπει είναι υπαρκτή. Εάν ο φάκελος ήταν προσαρτημένος,
        αποπροσαρτείται, μετονομάζεται και προσαρτείται πάλι.
    remove <ομάδες>
        Αποπροσαρτεί και αφαιρεί τη δυνατότητα κοινόχρηστων φακέλων από
        τις καθορισμένες ομάδες. Οι φάκελοι δεν διαγράφονται από το
        σύστημα αρχείων.
    remount <ομάδες>
        Επαναπροσαρτεί τους κοινόχρηστους φακέλους για όσες από τις
        καθορισμένες ομάδες έχει αλλάξει το όνομα ή το GID, και για όσες
        δεν ήταν προσαρτημένοι οι φάκελοί τους.
    mount <ομάδες>
        Προσαρτεί τους κοινόχρηστους φακέλους των καθορισμένων ομάδων.
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

# TODO: make it runnable from the console, process args etc.
    sf=SharedFolders(libuser.System())
    print sf.parse_mounts()
    print sf.list_shared(["alkisg", "a2", "a3"])
    print sf.list_mounted(["alkisg", "teachers"])
"""
    elif len(sys.argv) == 3 and (sys.argv[1] == '-e'):
        runas_user_script=sys.argv[2]
    elif len(sys.argv) >= 2:
        usage()
        sys.exit(1)
"""
