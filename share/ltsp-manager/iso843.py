#-*- coding: utf-8 -*-
# Copyright (C) 2012 Lefteris Nikoltsios <lefteris.nikoltsios@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>
# http://www.sete.gr/files/Media/Egkyklioi/040707Latin-Greek.pdf
# Transliterate and transcript made according iso843
# TODO: transform this library into a more generic one,
# that additionally checks the locale before doing any transliterations.

import re
import unicodedata

               
_mapping_letters = {
'α' : 'a', 'ά' : 'á', 'β' : 'v', 'γ' : 'g', 'δ' : 'd', 'ε' : 'e',
'έ' : 'é', 'ζ' : 'z', 'η' : 'i', 'ή' : 'í', 'θ' :'th', 'ι' : 'i',
'ί' : 'í', 'ϊ' : 'ï', 'ΐ' : 'ḯ', 'κ' : 'k', 'λ' : 'l', 'μ' : 'm',
'ν' : 'n', 'ξ' : 'x', 'ο' : 'o', 'ό' : 'ó', 'π' : 'p', 'ρ' : 'r',
'σ' : 's', 'ς' : 's', 'τ' : 't', 'υ' : 'y', 'ύ' : 'ý', 'ϋ' : 'ÿ',
'ΰ' : 'ÿ́', 'φ' : 'f', 'χ' :'ch', 'ψ' :'ps', 'ω' : 'o', 'ώ' : 'ó'}


_mapping_compine_letters = {
'γγ':'ng', 'γξ':'nx', 'γχ':'nch'}


_re_reg1 = 'α|ε|η'
_re_reg2 = 'υ|ύ'
_re_reg3 = 'β|γ|δ|ζ|λ|μ|ν|ρ|α|ά|ε|έ|η|ή|ι|ί|ϊ|ΐ|ο|ό|υ|ύ|ϋ|ΰ|ω|ώ'
_re_reg4 = 'θ|κ|ξ|π|σ|τ|φ|χ|ψ'
_re_reg5 = 'α|ά|ε|έ|ο|ό'
_re_reg6 = 'υ|ύ|ϋ|ΰ'
_re_reg7 = 'ο'
_re_reg8 = 'ύ|υ'

_reg1 = '('+_re_reg1.lower()+'|'+_re_reg1.upper()+')('+_re_reg2.lower()+'|'+_re_reg2.upper()+')('+_re_reg3.lower()+'|'+_re_reg3.upper()+')'

_reg2 = '('+_re_reg1.lower()+'|'+_re_reg1.upper()+')('+_re_reg2.lower()+'|'+_re_reg2.upper()+')('+_re_reg4.lower()+'|'+_re_reg4.upper()+')'

_reg3 = '^μπ|^Μπ|^ΜΠ|^μΠ|μπ$|Μπ$|ΜΠ$|μΠ$'

_reg4 = '^PS|^TH|^CH'

_reg5 = '(γ|Γ)(γ|ξ|χ|Γ|Ξ|Χ)'

_reg6 = '('+_re_reg5.lower()+'|'+_re_reg5.upper()+')('+_re_reg6.lower()+'|'+_re_reg6.upper()+')'

_reg7 = '('+_re_reg7.lower()+'|'+_re_reg7.upper()+')('+_re_reg8.lower()+'|'+_re_reg8.upper()+')'
        
        

def transcript(string, accents=True):
    if not isinstance(string, str):
        string = string.decode('utf-8')
    
    string = re.sub(_reg1, replace_v, string)
    string = re.sub(_reg2, replace_f, string)
    string = re.sub(_reg3, replace_b, string)
    string = re.sub(_reg5, replace_g, string)
    string = re.sub(_reg7, replace_ou, string)

    letters = []
    for letter in string:
        if letter in _mapping_letters:
            letters.append(_mapping_letters[letter].decode("utf-8"))
        elif letter.lower() in _mapping_letters:
            letters.append((_mapping_letters[letter.lower()].decode("utf-8")).upper())
        else:
            letters.append(letter)

    string = ''.join(letters)

    
    if re.match(_reg4, string):
        string = string.replace(string[1], string[1].lower())
    
    if accents:
        return string.encode("utf-8")
    else:
        return strip_accents(string).encode("utf-8")
        
    
       

def transliterate(string, accents=True):
    if not isinstance(string, str):
        string = string.decode('utf-8')

    string = re.sub(_reg6, replace_ou, string)
    

    letters = []
    for letter in string:
        if letter in _mapping_letters:
            letters.append(_mapping_letters[letter].decode("utf-8"))
        elif letter.lower() in _mapping_letters:
            letters.append((_mapping_letters[letter.lower()].decode("utf-8")).upper())
        else:
            letters.append(letter)

    string = ''.join(letters)

    
    if re.match(_reg4, string):
        string = string.replace(string[1], string[1].lower())
    
    if accents:
        return string.encode("utf-8")
    else:
        return strip_accents(string).encode("utf-8")



def replace_v(m):
    response = m.group(0)
    if m.group(2) == 'ύ' or m.group(2) == 'Ύ':
        if m.group(1) == 'α':
            response = response.replace(m.group(1), 'ά')
        elif m.group(1) == 'Α':
            response = response.replace(m.group(1), 'Ά')
        elif m.group(1) == 'ε':
            response = response.replace(m.group(1), 'έ')
        elif m.group(1) == 'Ε':
            response = response.replace(m.group(1), 'Έ')
        elif m.group(1) == 'η':
            response = response.replace(m.group(1), 'ή')
        elif m.group(1) == 'Η':
            response = response.replace(m.group(1), 'Ή')
        
    if m.group(2).islower():
        response = response.replace(m.group(2),'v')
        return response
    else:
        response = response.replace(m.group(2),'V')
        return response

def replace_f(m):
    response = m.group(0)
    if m.group(2) == 'ύ' or m.group(2) == 'Ύ':
        if m.group(1) == 'α':
            response = response.replace(m.group(1), 'ά')
        elif m.group(1) == 'Α':
            response = response.replace(m.group(1), 'Ά')
        elif m.group(1) == 'ε':
            response = response.replace(m.group(1), 'έ')
        elif m.group(1) == 'Ε':
            response = response.replace(m.group(1), 'Έ')
        elif m.group(1) == 'η':
            response = response.replace(m.group(1), 'ή')
        elif m.group(1) == 'Η':
            response = response.replace(m.group(1), 'Ή')
    
    if m.group(2).islower():
        response = response.replace(m.group(2),'f')
        return response
    else:
        response = response.replace(m.group(2),'F')
        return response

def replace_b(m):
    if m.group(0)[0].islower():
        return 'b'
    else:
        return 'B'


def replace_g(m):
    if m.group(0).islower():
        return _mapping_compine_letters[m.group(0)]
    elif m.group(0).isupper():
        return _mapping_compine_letters[m.group(0).lower()].upper()
    else:
        if m.group(0)[0].isupper() and m.group(0)[1].islower():
            response = _mapping_compine_letters[m.group(0).lower()]
            return response.replace(response[0], response[0].upper())
        elif m.group(0)[0].islower() and m.group(0)[1].isupper():
            response = _mapping_compine_letters[m.group(0).lower()]
            return response.replace(response[1], response[1].upper())     
             
             
def replace_ou(m):
    response = m.group(0)   
    if m.group(0)[1].islower(): 
        if m.group(0)[1] == 'ύ':
            response = response.replace(m.group(0)[1], 'ú')
            return response
        else:
            response = response.replace(m.group(0)[1], 'u')
            return response
    
    else:
        response = response.replace(m.group(0)[1],'U')
        return response


def strip_accents(string):
   return ''.join((c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn'))

