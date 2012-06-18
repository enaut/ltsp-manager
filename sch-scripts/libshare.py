#-*- coding: utf-8 -*-
import subprocess
from common import run_command

base = 'shared-folders'

def sf_list():
    success, res = run_command(base, 'list')
    if success:
        return res.split()
    else:
        return []

def sf_list_active():
    success, res = run_command(base, 'list-active')
    if success:
        return res.split()
    else:
        return []

def sf_add(group):
    return run_command([base, 'add', group])[0]
    
def sf_remove(group):
    return run_command([base, 'remove', group])[0]
    
def sf_move(group, to_group):
    return run_command([base, 'move', group, to_group])[0]
    
def sf_start(group=None):
    cmd = [base, 'start']
    if group is not None:
        cmd.append(group)
    return run_command(cmd)[0]
    
def sf_stop(group=None):
    cmd = [base, 'stop']
    if group is not None:
        cmd.append(group)
    return run_command(cmd)[0]
    
def sf_restart(group=None):
    cmd = [base, 'restart']
    if group is not None:
        cmd.append(group)
    return run_command(cmd)[0]

