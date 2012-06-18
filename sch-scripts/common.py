#-*- coding: utf-8 -*-

import subprocess

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

def greek_to_latin(name):
    mappings = {
    u'α' : 'a', u'ά' : 'a', u'β' : 'b', u'γ' : 'g', u'δ' : 'd',	u'ε' : 'e',
    u'έ' : 'e',	u'ζ' : 'z', u'η' : 'i', u'ή' : 'i', u'θ' :'th', u'ι' : 'i',
    u'ί' : 'i', u'ϊ' : 'i', u'ΐ' : 'i', u'κ' : 'k', u'λ' : 'l', u'μ' : 'm',
    u'ν' : 'n', u'ξ' : 'x', u'ο' : 'o', u'ό' : 'o', u'π' : 'p', u'ρ' : 'r', 
    u'σ' : 's', u'ς' : 's', u'τ' : 't', u'υ' : 'i', u'ύ' : 'i', u'ϋ' : 'i', 
    u'ΰ' : 'i', u'φ' : 'f', u'χ' :'ch', u'ψ' :'ps', u'ω' : 'o', u'ώ' : 'o'}

    name = name.lower()
    reg1 = u'(α|ε)(υ|ύ)(β|γ|δ|ζ|λ|μ|ν|ρ|α|ά|ε|έ|η|ή|ι|ϊ|ί|ΐ|ο|ό|υ|ϋ|ύ|ΰ|ω|ώ)'
    reg2 = u'(α|ε)(υ|ύ)(θ|κ|ξ|π|σ|τ|φ|χ|ψ)'
    reg3 = u'(ου|ού)'

    name = re.sub(reg1, u'\\1v\\3', name)
    name = re.sub(reg2, u'\\1f\\3', name)
    name = re.sub(reg3, u'ou', name)

    return ''.join([mappings[letter] if letter in mappings else letter for letter in name]).encode("utf-8")
