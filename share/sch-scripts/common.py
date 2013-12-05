#-*- coding: utf-8 -*-

import subprocess
import datetime
import re

def run_command(cmd):
    # Runs a command and returns either True, on successful
    # completion, or the whole stdout and stderr of the command, on error.
    
    # Popen doesn't like integers like uid or gid in the command line.
    cmdline = [str(s) for s in cmd]
    
    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = p.wait()
    if res == 0:
        return (True, p.stdout.read())
    else:
        print "Σφάλμα κατά την εκτέλεση εντολής:"
        print " $ %s" % ' '.join(cmdline)
        print p.stdout.read()
        err = p.stderr.read()
        print err
        if err == '':
            err = "\n"
        return (False, err)
    
def days_since_epoch():
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.today() - epoch).days

def date():
    return datetime.date.today()

