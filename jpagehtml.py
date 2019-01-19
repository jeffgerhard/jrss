# -*- coding: utf-8 -*-
"""
Created on Fri Jan  4 12:35:37 2019

@author: gerhardj

ok want to try using yattag
and tabular arrangement of the page

imagine it like --->

DATE AND TIME
INFO LINK (mini text links)
WIDGETS
TABS

then page content

figure out how to do an async page load for anything like bg images (for example,
    see https://github.com/verlok/lazyload)


"""
from yattag import Doc
from datetime import datetime
from datetime import timedelta
import inflect
from slugify import slugify
import base64
import random



def frame(settings):
    doc, tag, text, line = Doc().ttl()
    doc.asis('<!DOCTYPE html>')
    with tag('html', lang='en'):
        doc.asis(head(settings))
        with tag('body'):
            doc.asis(infobox())
            doc.asis(widgets(settings))
            with tag('div', klass='tab-switcher'):
                for sec in settings['sections']:
                    with tag('section', klass='tab'):
                        doc.stag('input', 'checked', ('type', 'radio'), ('id', slugify(sec)), name='tab-set')
                        with tag('label', ('for', slugify(sec)), onclick=''):
                            with tag('div', klass='rotate'):
                                text(sec)
                        with tag('div', klass='tab-content rand' +  str(random.randint(1, 5))):
                            # line('p', 'Add content here for ' + str(sec) + ' sort of like...')
                            secdict = settings['sections'][sec]
                            for curfeed in secdict:
                                for key in curfeed:
                                    with tag('div', ('id', slugify(key)), klass='feedblock'):
                                        if curfeed[key]['icon'] is not None:
                                            # much thanks to https://stackoverflow.com/a/49475135
                                            encoded = base64.b64encode(curfeed[key]['icon']).decode() 
                                            doc.stag('img', src='data:image/png;base64,{}'.format(encoded), klass='icon')
                                        line('h4', key)
                                        # see what kind of authors there are (if any)...
                                        authors = []
                                        authortype = None
                                        for entry in curfeed[key]['entries']:
                                            if entry[5]:
                                                authors.append(entry[5])
                                        if len(authors) > 0:
                                            if len(set(authors)) == 1:
                                                authortype = 'single'
                                            else:
                                                spaced = 0
                                                kinja = False
                                                for au in authors:
                                                    if ' ' in au:
                                                        spaced += 1
                                                    if ' on ' in au and ', shared' in au:
                                                        kinja = True
                                                if kinja is True:
                                                    authortype = 'kinja'
                                                else:
                                                    if spaced == 0:
                                                        authortype = 'unspaced'
                                                    elif spaced < (len(authors) // 2):
                                                        authortype = 'unspaced'
                                                    else:
                                                        authortype = 'spaced'
                                        for entry in curfeed[key]['entries'][:15]:
                                            with tag('ul', klass='entries'):
                                                with tag('li'):
                                                    with tag('a', href=entry[2], target='_blank', klass='tooltip', title=checkNulls(entry[3])):
#                                                         text(entry[0])
#                                                    with tag('a', href=entry[2], target='_blank', klass='tooltip', title=checkNulls(cleaner.clean(entry[3]))):
#                                                        doc.asis(cleaner.clean(entry[0]))
                                                        doc.asis(entry[0])
                                                    if entry[5]:
                                                        if authortype != 'single':
                                                            with tag('span', klass='author'):
                                                                doc.asis(' ')
                                                                doc.asis(cleanauthors(authortype, entry[5]))
                                                                doc.asis(' &middot;')
                                                    with tag('small', klass='feeddate'):
                                                        text(' ', entry[1])

                            with tag('p', onclick='window.scrollTo(0, 0);', klass='bottom'):
                                text('[return to top]')
#                            with tag('div', klass='feedblock'):
#                                for _ in settings['sections'][sec]:
#                                    with tag('ul'):
#                                        line('li', _[1])
#                                    
    return doc.getvalue()

def checkNulls(x):
    if x:
        return x
    else:
        return ''

def head(settings):
    doc, tag, text, line = Doc().ttl()
    with tag('head'):
        doc.stag('meta', charset='utf-8')
        doc.stag('meta', name='viewport', content='width=device-width, initial-scale=1, maximum-scale=1')
        doc.stag('meta', name='referrer', content="no-referrer")
        doc.stag('meta', name='robots', content="noindex, nofollow")
        with tag('title'):
            text('Jrss ~ v.', settings['version'])
        doc.stag('link', rel='stylesheet', href='style/style.css')
#        with tag('script', ('type', 'text/javascript')):
#            text('')
    return doc.getvalue()

def infobox():
    doc, tag, text, line = Doc().ttl()
    with tag('div', ('id', 'infobox'), klass='info'):
        now = datetime.now() - timedelta(hours=5)  # THIS NEEDS TO BE USER CONFIGURABLE!!!
        updatestring = now.strftime('%a') + '., ' + now.strftime('%b') + '. '
        updatestring += inflect.engine().ordinal(now.day) + ' '
        updatestring += str(int(now.strftime('%I'))) + ':' + now.strftime('%M') + ' '
        updatestring += now.strftime('%p')
        with tag('p', klass='datetime'):
            text(updatestring)
            with tag('span', ('id', 'refresh'), onclick='location.reload(true)'):
                with tag('small'):
                    text(' refresh ')
        with tag('ul', klass='navigator'):
            with tag('li'):
                with tag('a', href='logs/log.txt'):
                    text('log')
            with tag('li'):
                with tag('a', href='https://github.com/jeffgerhard/jrss'):
                    text('src')
        doc.stag('br', style='clear: both;')
    return doc.getvalue()

def widgets(settings):
    doc, tag, text, line = Doc().ttl()
    doc.asis('<!-- insert widgets here -->')    
    return doc.getvalue()

def cleanauthors(authortype, a):
    def words2caps(x):
        if ' ' not in x:
            return x.upper()
        segs = list()
        words = x.split(' ')
        for word in words:
            if word.lower() in ['the', 'a', 'an', 'of', 'for', 'on', 'by', 'to',
                                'from', 'as', 'and', 'with']:
                segs.append(word)
            else:
                segs.append(word.upper())
        return ' '.join(segs)
    if authortype:
        if authortype == 'kinja':
            if ' on ' in a and ', shared by' in a:
                a = a.split(', shared by')[0]
                return words2caps(a.split(' on ')[0]) + ' on ' + a.split(' on ')[1]
        elif authortype == 'unspaced':
            return a
    if '@' in a and '(' in a:  # email address and then a name in parentheses...
        a = a[a.find('(')+1:a.find(')')]
    if '(' in a:
        # if still has parenthetical info don't wanna capitalize it
        return words2caps(a.split('(')[0]) + '(' + a.split(')')[1]
    if ' ' in a:
        return words2caps(a)
    return a

if __name__ == "__main__":
    print('This is the HTML generator code; currently it cannot be run as a standalone module.')
    
