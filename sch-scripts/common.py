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

def greek_to_latin(name):
    # TODO: Follow the rules of ELOT 743:
    # http://www.sete.gr/files/Media/Egkyklioi/040707Latin-Greek.pdf
    if not isinstance(name, unicode):
        name = name.decode('utf-8')

    mappings_lowercase = {
    u'α' : 'a', u'ά' : 'á', u'β' : 'v', u'γ' : 'g', u'δ' : 'd', u'ε' : 'e',
    u'έ' : 'é', u'ζ' : 'z', u'η' : 'i', u'ή' : 'í', u'θ' :'th', u'ι' : 'i',
    u'ί' : 'í', u'ϊ' : 'ï', u'ΐ' : 'ḯ', u'κ' : 'k', u'λ' : 'l', u'μ' : 'm',
    u'ν' : 'n', u'ξ' : 'x', u'ο' : 'o', u'ό' : 'ó', u'π' : 'p', u'ρ' : 'r',
    u'σ' : 's', u'ς' : 's', u'τ' : 't', u'υ' : 'y', u'ύ' : 'ý', u'ϋ' : 'ÿ',
    u'ΰ' : 'ÿ́', u'φ' : 'f', u'χ' :'ch', u'ψ' :'ps', u'ω' : 'o', u'ώ' : 'ó',
    u'γγ':'ng', u'γξ':'nx', u'γχ':'nch'}

    re_reg1 = u'α|ε|η'
    re_reg2 = u'υ|ύ'
    re_reg3 = u'β|γ|δ|ζ|λ|μ|ν|ρ|α|ά|ε|έ|η|ή|ι|ί|ϊ|ΐ|ο|ό|υ|ύ|ϋ|ΰ|ω|ώ'
    re_reg4 = u'θ|κ|ξ|π|σ|τ|φ|χ|ψ'
    re_reg5 = u'μπ'

    reg1 = '('+re_reg1.lower()+'|'+re_reg1.upper()+')('+re_reg2.lower()+'|'+re_reg2.upper()+')('+re_reg3.lower()+'|'+re_reg3.upper()+')'
    
    reg2 = '('+re_reg1.lower()+'|'+re_reg1.upper()+')('+re_reg2.lower()+'|'+re_reg2.upper()+')('+re_reg4.lower()+'|'+re_reg4.upper()+')'
    
    reg3 = u'^μπ|^Μπ|^ΜΠ|^μΠ|μπ$|Μπ$|ΜΠ$|μΠ$'

    name = re.sub(reg1, replace_v, name)
    name = re.sub(reg2, replace_f, name)
    name = re.sub(reg3, replace_b, name)

    letters = []
    for letter in name:
        if letter in mappings_lowercase:
            letters.append(mappings_lowercase[letter].decode("utf-8"))
        elif letter.lower() in mappings_lowercase:
            letters.append((mappings_lowercase[letter.lower()].decode("utf-8")).upper())
        else:
            letters.append(letter)

    name = ''.join(letters)

    reg4 = '^PS|^TH|^CH'

    if re.match(reg4, name):
        name = name.replace(name[1], name[1].lower())
    
    return name.encode("utf-8")
    
   
def replace_v(m):
    if m.group(2).islower():
        response = m.group(0)
        if m.group(2) == u'ύ':
            if m.group(1) == u'α':
                response = response.replace(m.group(1), u'ά')
            elif m.group(1) == u'ε':
                response = response.replace(m.group(1), u'έ')
            elif m.group(1) == u'η':
                response = response.replace(m.group(1), u'ή')
        response = response.replace(m.group(2),u'v')
        return response
    else:
        response = m.group(0)
        if m.group(2) == u'ύ':
            if m.group(1) == u'α':
                response = response.replace(m.group(1), u'ά')
            elif m.group(1) == u'ε':
                response = response.replace(m.group(1), u'έ')
            elif m.group(1) == u'η':
                response = response.replace(m.group(1), u'ή')
        response = response.replace(m.group(2),u'V')
        return response

def replace_f(m):
    if m.group(2).islower():
        response = m.group(0)
        if m.group(2) == u'ύ':
            if m.group(1) == u'α':
                response = response.replace(m.group(1), u'ά')
            elif m.group(1) == u'ε':
                response = response.replace(m.group(1), u'έ')
            elif m.group(1) == u'η':
                response = response.replace(m.group(1), u'ή')
        response = response.replace(m.group(2),u'f')
        return response
    else:
        response = m.group(0)
        if m.group(2) == u'ύ':
           if m.group(1) == u'α':
                response = response.replace(m.group(1), u'ά')
           elif m.group(1) == u'ε':
                response = response.replace(m.group(1), u'έ')
           elif m.group(1) == u'η':
                response = response.replace(m.group(1), u'ή')
        response = response.replace(m.group(2),u'F')
        return response

def replace_b(m):
    if m.group(0)[0].islower():
        return u'b'
    else:
        return u'B'
    
def days_since_epoch():
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.today() - epoch).days

def date():
    return datetime.date.today()

