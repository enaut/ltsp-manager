# This File is part of the ltsp-manager.
#
# Copyright 2012-2018 by it's authors.
#
# Licensed under GNU General Public License 3.0 or later.
# Some rights reserved. See COPYING, AUTHORS.

import datetime
import gettext
import locale
import re
import subprocess
import sys

try:
    gettext.install('ltsp-manager')
except:
    print("Installing gettext without unicode")
    gettext.install('ltsp-manager')
locale.textdomain('ltsp-manager')

def run_command(cmd, poll=False):
    # Runs a command and returns either True, on successful
    # completion, or the whole stdout and stderr of the command, on error.
    # If poll is set return only the process
    
    # Popen doesn't like integers like uid or gid in the command line.
    cmdline = [str(s) for s in cmd]
    
    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not poll:
        res = p.wait()
        if res == 0:
            return True, p.stdout.read().decode('utf-8')
        else:
            sys.stderr.write("Error while executing command:\n" +
                " $ %s" % ' '.join(cmdline) + "\n")
            sys.stderr.write(p.stdout.read().decode('utf-8'))
            err = p.stderr.read().decode('utf-8')
            sys.stderr.write(err)
            if err == '':
                err = "\n"
            return False, err
    else:
        return p
    
def days_since_epoch():
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.today() - epoch).days

def date():
    return datetime.date.today()
