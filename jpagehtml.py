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
                                        for entry in curfeed[key]['entries'][:15]:
                                            with tag('ul', klass='entries'):
                                                with tag('li'):
                                                    with tag('a', href=entry[2], target='_blank', klass='tooltip', title=checkNulls(entry[3])):
                                                        text(entry[0])
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
        with tag('title'):
            text('JPage ~ v.', settings['version'])
        doc.stag('link', rel='stylesheet', href='style/style.css')
#        with tag('script', ('type', 'text/javascript')):
#            text('')
    return doc.getvalue()

def infobox():
    doc, tag, text, line = Doc().ttl()
    with tag('div', ('id', 'infobox'), klass='info'):
        now = datetime.now()
        updatestring = now.strftime('%a') + '., ' + now.strftime('%b') + '. '
        updatestring += inflect.engine().ordinal(now.day) + ' '
        updatestring += str(int(now.strftime('%I'))) + ':' + now.strftime('%M') + ' '
        updatestring += now.strftime('%p')
        with tag('p', klass='datetime'):
            text(updatestring)
        with tag('ul', klass='navigator'):
            with tag('li'):
                with tag('a', href='logs/log.txt'):
                    text('log')
            with tag('li'):
                with tag('a', href='https://github.com/jeffgerhard/jpage'):
                    text('src')
        doc.stag('br', style='clear: both;')
    return doc.getvalue()

def widgets(settings):
    doc, tag, text, line = Doc().ttl()
    doc.asis('<!-- insert widgets here -->')    
    return doc.getvalue()

if __name__ == "__main__":
    sections = dict()
    sections['News'] = [{'BBC News': {'icon': 'some string',
                                      'entries': [('Trump ready for shutdown', '4 hours ago', 'http://alink', 'summary'),
                                                  ('Subarimala: Women who defied...', '7 hours ago', 'http://asdafdd', 'summary'),
                                                  ('Migrant crisis: Illegal entries to EU', '6 hours ago', 'http://asfadsfdfs', 'summary')]}
    },
        {'LA Times': {'icon': 'some string',
                      'entries': [('Editorial staff directory', '10 minutes ago', 'http://adssdfadsf', 'summary'),
                                  ('The week ahead in SoCla classical music', '35 minutes ago', 'http:/adsfdsf', 'summary')]}}
        ]
    
    sections['Poindextrous'] = [{'Metafilter': {'icon': 'some string',
            'entries': [('"I\'m so excited because I love mess!"', '1 hour ago', 'http://asdffd', 'summary'),
                        ('Friday Flash Fun (remember those?)', '4 hours ago', 'http:/adsfdsfa', 'summary')]}}]
    settings = {'version': '0.1', 'sections': sections}
    
