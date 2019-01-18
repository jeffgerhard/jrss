# -*- coding: utf-8 -*-
"""
jpage 2019

run it in python on server via cron jobs
use a sqlite db
update static html pages and save to a public web directory
figure out an authentication/login scheme
use css navigation a la https://www.adobe.com/devnet/archive/html5/articles/using-form-elements-and-css3-to-replace-javascript.html
monitor feeds and adjust frequency of checking; hide ones that havent been updated in ages
set a hard max on number of feeds to include; suggest running multi instances if necessary
include widgets; i.e., weather info https://openweathermap.org/api
look into sports score apis
allow some art touches; e.g., this isn't happiness tumblr
do a full-on NYT emulation incl. front page
consider comics
figure out async loading -- first load front page content; then widgets, then secondary pages

"""

# SET UP FEEDS TABLE

import sqlite3
import os
import requests
import favicon
# import json
from PIL import Image
from io import BytesIO
import feedparser
#from dateutil.parser import parse
#from datetime import datetime
import time
import arrow
import sys
import re
if 'duckduckgo' in sys.modules:
    import duckduckgo  # https://github.com/taciturasa/duckduckgo-python3
from bleach import Cleaner
cleaner = Cleaner(tags=['i', 'em', 'b', 'br', 'p', 'strong', 'code', 'abbr'],
                  attributes={'*': ['style'] },
                  styles=['color', 'background-color', 'font', 'font-family', 
                          'font-weight', 'font-size'],
                  strip=True)


def schema(conn):
    statements = list()
    statements.append("""CREATE TABLE schema 
        (id INTEGER PRIMARY KEY,
        version char(100) NOT NULL)   
    """)
    statements.append("""CREATE TABLE categories 
        (id INTEGER PRIMARY KEY,
        category_name char(100) NOT NULL,
        style char(25))
    """)
    statements.append("""CREATE TABLE feeds
        (id INTEGER PRIMARY KEY,
        icon BLOB,
        feed_name char(100) NOT NULL,
        link char(100) NOT NULL,
        category char(100) NOT NULL,
        filters char(500),
        success char(5),
        newest_feed char(50),
        etag char(50),
        lastmod char(100))
    """)
    statements.append("""CREATE TABLE entries
        (id INTEGER PRIMARY KEY,
        entry_uri char(400),
        guid char(300),
        date char(23),
        headline char(400),
        summary char(1000),
        feed_id INTEGER,
        authors char(400))
    """)
    for statement in statements:
        conn.execute(statement)    

def populate(cursor):
    log = list()
    with open('feeds/feeds.csv', 'r') as fh:
        feeds = [_ for _ in fh.read().splitlines() if _]
    cursor.execute('SELECT * FROM feeds')
    results = cursor.fetchall()  
    updates = list()
    for f in feeds:
        found = False
        flist = f.split(',')
        for r in results:
            if r[2] == flist[0]:
                log.append('found ' + str(flist[0]) + ' in db.')
#                print('found', flist[0], 'in db.')
                found = True
        if found is False:
            updates.append(tuple(flist))
 #           print('Adding', flist[0], 'to db.')
            log.append('Adding ' + str(flist[0]) + ' to db.')
    if len(updates) > 0:
        cursor.executemany('INSERT INTO feeds (feed_name, category, link, filters) VALUES (?, ?, ?, ?)', updates)
    cursor.execute('INSERT INTO schema (version) VALUES (?)', (checkversion(),))
    return log

def getIcon(cursor, feed):
    iconurl = None
    if feed[1]:
        return 'Icon already saved in db for ' + feed[2]
    uri = feed[3]
    if 'feedburner' in uri and 'duckduckgo' in sys.modules: 
        r = duckduckgo.query(feed[2])
        if r.type == 'answer':
            return r.results[0].url        
        if uri is None:
            return 'No icon found for ' + feed[2]
    link = 'http://' + uri.split('//')[1].split('/')[0] + '/'
    try:
        icons = favicon.get(link)
#        ilist = [i.height for i in icons]
#        size = min(ilist, key=lambda x:abs(x-100)) # grab the one closest to 100px
#        for i in icons:
#            if i.height == size:
#                iconurl = i.url
        iconurl = icons[0].url
    except:
        pass
    if iconurl:
        img_data = requests.get(iconurl).content
        if img_data:
            image = Image.open(BytesIO(img_data))
            image.thumbnail((40, 80))
            imgByteArr = BytesIO()  # this stuff via https://stackoverflow.com/a/33117447
            image.save(imgByteArr, format='PNG')
            imgByteArr = imgByteArr.getvalue()
            update = (imgByteArr, feed[0])
            cursor.execute('UPDATE feeds SET icon=? WHERE id=?', update)
            return 'Added icon for ' + link
    return 'No icon found for ' + link

def checkFeeds(cursor):
    log = ['\n\n------------------------------\nChecking feeds...']
    alerts = list()
    cursor.execute('SELECT id, link, etag, lastmod FROM feeds')
    rows = cursor.fetchall()
    updates = list()
    for row in rows:
        checkentries = True
        link = row[1]
        note = 'Parsing ' + link + ': '
        if row[2]:
            note += '(comparing etag...)'
            d = feedparser.parse(row[1], etag=row[2])
        elif row[3]:
            d = feedparser.parse(row[1], modified=row[3])
            note += '(comparing lastmod...)'
        else:
            d = feedparser.parse(row[1])
        if d.status == 304:
            note += '\n\tUnmodified. (Etag or modified date match.)'
            checkentries = False
        elif d.status == 302:
            note += '\n\t' + row[1] + ' was temporarily redirected based on a 302 status.'
        elif d.status == 301:
            alerts.append('\n * ' + link + ' HAS A 301 PERMENANENT REDIRECT\n\tUpdated to ' + d.href)
#            print('\n\t* trying to update link in database for', link)
            cursor.execute('UPDATE feeds SET link=? WHERE id=?', (d.href, row[0],))
        elif d.status == 401:
            alerts.append('\n *** ' + row[1] + ' HAS A 410 GONE STATUS (ADD CODE TO TRACK THIS AND LATER DELETE THE FEED????)')
            checkentries = False
        if 'etag' in d:
            if row[2] != d.etag:
                cursor.execute('UPDATE feeds SET etag=? WHERE id=?', (d.etag, row[0],))
        if 'modified' in d:
            if row[3] != d.modified:
                cursor.execute('UPDATE feeds SET lastmod=? WHERE id=?', (d.modified, row[0],))
        if checkentries is True:
            if d.entries:
                note += '\n\tFound feed (title: ' + d.feed.title
                note += ') with ' + str(len(d.entries)) + ' entries.\n\t'
                existing_entries = 0
                new_entries = 0
                for _ in d.entries:
                    update = False
                    if 'guid' in _:
                        update = True
                        guid = _.guid
                        cursor.execute('SELECT date FROM entries WHERE guid=?', (guid,))
                        results = cursor.fetchone()
                        if results:
                            update = False
                            existing_entries += 1
                    elif 'link' in _:
                        update = True
                        guid = _.link
                        cursor.execute('SELECT date FROM entries WHERE entry_uri=?', (guid,))
                        results = cursor.fetchone()
                        if results:
                            update = False
                            existing_entries += 1
                    if update:
                        new_entries += 1
                        epochdate = 0
                        feed_id = row[0]
                        if 'published_parsed' in _:
                            try:
                                epochdate = time.mktime(_.published_parsed)
                            except:
                                pass
                        elif 'updated_parsed' in _:
                            try:
                                epochdate = time.mktime(_.updated_parsed)
                            except:
                                pass
                        if 'summary' in _:
                            summary = re.sub(re.compile('<.*?>'), '', _.summary)[:400]
                            #summary = cleaner.clean(_.summary[:500])
#                        elif 'authors' in _:
#                            author = cleaner.clean(', '.join(_.authors)[:400])
                        else: 
                            summary = None
                        if 'author' in _:
                            author = cleaner.clean(_.author[:400])
                        else:
                            author = None
                        updater = [_.link, guid, epochdate, cleaner.clean(_.title[:399]), summary, feed_id, author]
                        updates.append(tuple(updater))
                if new_entries > 0:
                    note += str(new_entries) + ' added to db. '
                if existing_entries > 0:
                    note += str(existing_entries) + ' were already in the db.'                
            else:
                alerts.append('\n* FAILED FEED: couldn\'t parse ' + row[1] + '.')
        log.append(note)
    if len(updates) > 0:
        cursor.executemany('INSERT INTO entries (entry_uri, guid, date, headline, summary, feed_id, authors) VALUES (?, ?, ?, ?, ?, ?, ?)', updates)
        return alerts, log, updates


def buildSettings(cursor, gap=700000):
    settings = dict()
    sections = dict()
    feeds = dict()
    cursor.execute('SELECT * FROM entries')
    rows = cursor.fetchall()
    for r in rows:
        entryfeedid = r[6]
        cursor.execute('SELECT icon, feed_name, category FROM feeds WHERE id=?', (entryfeedid,))
        feeddata = cursor.fetchone()
        if feeddata[1] not in feeds:
            feeds[feeddata[1]] = list()
        timestring = arrow.get(float(r[3])).to('US/Eastern').humanize() # NEED TO MAKE THIS CONFIGURABLE
        #timestring = arrow.get(float(r[3])).shift(hours=-5).humanize() # ugh the timezone issue is tricky!
        if abs(time.time() - float(r[3])) < gap:
            feeds[feeddata[1]].append(tuple([r[4], timestring, r[1], r[5], r[3], r[7]])) # keep the epoch time for sorting
    for f in [_ for _ in feeds if len(feeds[_])>0]:
        cursor.execute('SELECT icon, category FROM feeds WHERE feed_name=?', (f,))
        feeddata = cursor.fetchone()
        sortedfeed = sorted(feeds[f], key=lambda x: x[4], reverse=True)
        # skip feeds that haven't been updated in a while...
        if abs(time.time() - float(sortedfeed[0][4])) < gap: # around 8 days
            if feeddata[1] not in sections:
                sections[feeddata[1]] = list()
            sections[feeddata[1]].append({f: {'entries': sortedfeed, 'icon': feeddata[0]}})
    settings['version'] = checkversion()
    settings['sections'] = sections
    return feeds, settings

def checkversion():
    with open('data/version.txt', 'r') as fh:
        return fh.read()


def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
#via http://stackoverflow.com/a/31631711
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)


def dbsize(dbfile):
    return humanbytes(os.stat(dbfile).st_size)

if __name__ == "__main__":
    feedparser.USER_AGENT = 'jrss/' + checkversion() + ' +https://github.com/jeffgerhard/jrss'
    # make directories if they don't exist:
    if not os.path.exists('feeds/feeds.csv'):
        raise UserWarning('There are no feeds! See setup documentation for help setting up and a demo.')
    for _ in ['data', 'logs', 'widgets']:
        os.makedirs(_, exist_ok=True)
    dbfile = 'feeds/feeds.db'
    log = list()
    alerts = ['ALERTS:']
    conn = sqlite3.connect(dbfile) # Warning: This file is created in the current directory
    cursor = conn.cursor()
    dbsummary = ['\nBeginning database size: ' + dbsize(dbfile)]  # later also add db details like no. of entries and feeds
    # first let's see if the db is set up
    try:
        cursor.execute('SELECT version FROM schema')
        results = cursor.fetchone()
        if results[0] == checkversion():
            proceed = True
        else:
            proceed = False
        #print('found schema')
    except:
        proceed = False
    if proceed is False:
        cursor.close()
        conn.close()
        os.remove(dbfile)
        conn = sqlite3.connect(dbfile) # Warning: This file is created in the current directory
        cursor = conn.cursor()        
        schema(conn)  # set up table
        #print('Generated schema.')
    # next populate the db with stuff... can do this via csvs i think..
    # set up db
    setuplog = ['\n\nSETUP (non-critical info here...):\n\nChecking the feeds csv...']
    setuplog += populate(cursor)
    # do the favicons
    cursor.execute('SELECT * FROM feeds')
    feeds = cursor.fetchall()
    setuplog.append ('\n\nChecking favicons...')
    for feed in feeds:
        setuplog.append(getIcon(cursor, feed))
    # now let's try to pull in some feed content!
    a, l, updates = checkFeeds(cursor)
    log += l
    alerts += a
#    cats, pages, results = buildModules(cursor)
    conn.commit()
    from jpagehtml import frame
    feeds, settings = buildSettings(cursor, gap=108000) 
    x = frame(settings)
    # do some database maintenance
    # look at the feeds already parsed above
    updates = list()
    deletes = list()
    for f in [_ for _ in feeds if len(feeds[_])>0]:
        sortedlist = sorted(feeds[f], key=lambda x: x[4])
        lastupdate = sortedlist[-1][4]
#        log.append(f + ' last updated ' + arrow.get(lastupdate).shift(hours=-5).humanize())
        updates.append(tuple([lastupdate, 'True', f]))
        if len(sortedlist) > 40:
            for entry in sortedlist[:len(sortedlist)-39]:
                deletes.append(tuple([entry[0], entry[4]]))
    cursor.executemany('DELETE FROM entries WHERE headline=? AND date=?', deletes)
    log.append('Purged ' + str(len(deletes)) + ' entries.')
    cursor.executemany('UPDATE feeds SET newest_feed=?, success=? WHERE feed_name=?', updates)
    conn.commit()    
    dbsummary.append('\nFinal database size: ' + dbsize(dbfile))
    cursor.execute('SELECT feed_name, newest_feed FROM feeds ORDER BY newest_feed')
    results = cursor.fetchall()
    feedsummary = ['\n\nSummary of feeds in the database after latest check:\n']
    for r in reversed(results):
        if r[1]:
            feedsummary.append(r[0] + ' last updated ' + arrow.get(r[1]).to('US/Eastern').humanize() + '.') # TIME ZONE INFO HAS TO BE USER CONFIG'D
    conn.close()
    with open('index.html', 'w', encoding='utf-8') as fh:
        fh.write(x)
    finallog = alerts + dbsummary + feedsummary + log + setuplog
    with open('logs/log.txt', 'w') as fh:
        fh.write('\n'.join(finallog))
    now = arrow.utcnow()
    logpath = os.path.join('logs', str(now.year), str(now.month), str(now.day))
    os.makedirs(logpath, exist_ok=True)
    with open(os.path.join(logpath, 'full.log'), 'a') as fh:
        fh.write('\n\n' + '-' * 12 + arrow.utcnow().format() + '-' * 12 + '\n\n' + '\n'.join(finallog))

