#-*- coding: utf-8 -*-

# http://www.sete.gr/files/Media/Egkyklioi/040707Latin-Greek.pdf
# Transliterate and transcript made according iso843

import re
import unicodedata

               
_mapping_letters = {
u'α' : 'a', u'ά' : 'á', u'β' : 'v', u'γ' : 'g', u'δ' : 'd', u'ε' : 'e',
u'έ' : 'é', u'ζ' : 'z', u'η' : 'i', u'ή' : 'í', u'θ' :'th', u'ι' : 'i',
u'ί' : 'í', u'ϊ' : 'ï', u'ΐ' : 'ḯ', u'κ' : 'k', u'λ' : 'l', u'μ' : 'm',
u'ν' : 'n', u'ξ' : 'x', u'ο' : 'o', u'ό' : 'ó', u'π' : 'p', u'ρ' : 'r',
u'σ' : 's', u'ς' : 's', u'τ' : 't', u'υ' : 'y', u'ύ' : 'ý', u'ϋ' : 'ÿ',
u'ΰ' : 'ÿ́', u'φ' : 'f', u'χ' :'ch', u'ψ' :'ps', u'ω' : 'o', u'ώ' : 'ó'}


_mapping_compine_letters = {
u'γγ':'ng', u'γξ':'nx', u'γχ':'nch'}


_re_reg1 = u'α|ε|η'
_re_reg2 = u'υ|ύ'
_re_reg3 = u'β|γ|δ|ζ|λ|μ|ν|ρ|α|ά|ε|έ|η|ή|ι|ί|ϊ|ΐ|ο|ό|υ|ύ|ϋ|ΰ|ω|ώ'
_re_reg4 = u'θ|κ|ξ|π|σ|τ|φ|χ|ψ'
_re_reg5 = u'α|ά|ε|έ|ο|ό'
_re_reg6 = u'υ|ύ|ϋ|ΰ'

_reg1 = '('+_re_reg1.lower()+'|'+_re_reg1.upper()+')('+_re_reg2.lower()+'|'+_re_reg2.upper()+')('+_re_reg3.lower()+'|'+_re_reg3.upper()+')'

_reg2 = '('+_re_reg1.lower()+'|'+_re_reg1.upper()+')('+_re_reg2.lower()+'|'+_re_reg2.upper()+')('+_re_reg4.lower()+'|'+_re_reg4.upper()+')'

_reg3 = u'^μπ|^Μπ|^ΜΠ|^μΠ|μπ$|Μπ$|ΜΠ$|μΠ$'

_reg4 = '^PS|^TH|^CH'

_reg5 = u'(γ|Γ)(γ|ξ|χ|Γ|Ξ|Χ)'

_reg6 = '('+_re_reg5.lower()+'|'+_re_reg5.upper()+')('+_re_reg6.lower()+'|'+_re_reg6.upper()+')'
        
        

def transliterate(string, accents=True):
    if not isinstance(string, unicode):
        string = string.decode('utf-8')
    
    string = re.sub(_reg1, replace_v, string)
    string = re.sub(_reg2, replace_f, string)
    string = re.sub(_reg3, replace_b, string)
    string = re.sub(_reg5, replace_g, string)

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
        
    
       

def transcript(string, accents=True):
    if not isinstance(string, unicode):
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
    if m.group(2) == u'ύ' or m.group(2) == u'Ύ':
        if m.group(1) == u'α':
            response = response.replace(m.group(1), u'ά')
        elif m.group(1) == u'Α':
            response = response.replace(m.group(1), u'Ά')
        elif m.group(1) == u'ε':
            response = response.replace(m.group(1), u'έ')
        elif m.group(1) == u'Ε':
            response = response.replace(m.group(1), u'Έ')
        elif m.group(1) == u'η':
            response = response.replace(m.group(1), u'ή')
        elif m.group(1) == u'Η':
            response = response.replace(m.group(1), u'Ή')
        
    if m.group(2).islower():
        response = response.replace(m.group(2),u'v')
        return response
    else:
        response = response.replace(m.group(2),u'V')
        return response

def replace_f(m):
    response = m.group(0)
    if m.group(2) == u'ύ' or m.group(2) == u'Ύ':
        if m.group(1) == u'α':
            response = response.replace(m.group(1), u'ά')
        elif m.group(1) == u'Α':
            response = response.replace(m.group(1), u'Ά')
        elif m.group(1) == u'ε':
            response = response.replace(m.group(1), u'έ')
        elif m.group(1) == u'Ε':
            response = response.replace(m.group(1), u'Έ')
        elif m.group(1) == u'η':
            response = response.replace(m.group(1), u'ή')
        elif m.group(1) == u'Η':
            response = response.replace(m.group(1), u'Ή')
    
    if m.group(2).islower():
        response = response.replace(m.group(2),u'f')
        return response
    else:
        response = response.replace(m.group(2),u'F')
        return response

def replace_b(m):
    if m.group(0)[0].islower():
        return u'b'
    else:
        return u'B'


def replace_g(m):
    if m.group(0) in _mapping_compine_letters:
        return _mapping_compine_letters[m.group(0)]

def replace_ou(m):
    response = m.group(0)   
    if m.group(0)[1].islower():
        response = response.replace(m.group(0)[1],u'u')
        return response
    else:
        response = response.replace(m.group(0)[1],u'U')
        return response


def strip_accents(string):
   return ''.join((c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn'))

