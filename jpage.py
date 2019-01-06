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
if 'duckduckgo' in sys.modules:
    import duckduckgo  # https://github.com/taciturasa/duckduckgo-python3



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
        newest_feed char(50))
    """)
    statements.append("""CREATE TABLE entries
        (id INTEGER PRIMARY KEY,
        entry_uri char(400),
        guid char(300),
        date char(23),
        headline char(400),
        summary char(1000),
        feed_id INTEGER)
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
        uri = duckit(feed[2])
        r = duckduckgo.query(x)
        if r.type == 'answer':
            return r.results[0].url        
        if uri is None:
            return 'No icon found for ' + feed[2]
    link = 'http://' + uri.split('//')[1].split('/')[0] + '/'
    #print('attemping', link)
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
    cursor.execute('SELECT id, link FROM feeds')
    rows = cursor.fetchall()
    updates = list()
    for row in rows:
        d = feedparser.parse(row[1])
        if d.entries:
#            print('----------------------')
#            print(d.feed.title)
#            print('(found', len(d.entries), 'entries.)')
            note = 'Parsing ' + str(row[1]) + ': '
            note += '\n\tFound feed (title: ' + d.feed.title
            note += ') with ' + str(len(d.entries)) + ' entries.\n\t'
            existing_entries = 0
            new_entries = 0
            for _ in d.entries:
#               try to match on guid
                update = False
                if 'guid' in _:
                    update = True
                    guid = _.guid
                    cursor.execute('SELECT date FROM entries WHERE guid=?', (guid,))
                    results = cursor.fetchone()
                    if results:
                        #print('Already in db.')
                        update = False
                        existing_entries += 1
                elif 'link' in _:
                    update = True
                    guid = _.link
                    cursor.execute('SELECT date FROM entries WHERE entry_uri=?', (guid,))
                    results = cursor.fetchone()
                    if results:
                        #print('Already in db.')
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
                        summary = _.summary[:500]
                    else: 
                        # print('No summary for', _.link)
                   #     log.append('No summary found for feed: ' + str(_.link))
                        summary = None
                    updater = [_.link, guid, epochdate, _.title[:399], summary, feed_id]
                    updates.append(tuple(updater))
            if new_entries > 0:
                note += str(new_entries) + ' added to db. '
            if existing_entries > 0:
                note += str(existing_entries) + ' were already in the db.'                
            log.append(note)
        else:
            alerts.append('\n*** FAILED FEED: couldn\'t parse ' + row[1] + '.')
            # print('\n\n*** couldn\'t parse ' + row[1])
    if len(updates) > 0:
        cursor.executemany('INSERT INTO entries (entry_uri, guid, date, headline, summary, feed_id) VALUES (?, ?, ?, ?, ?, ?)', updates)
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
        #timestring = arrow.get(float(r[3])).to('US/Eastern').humanize()
        timestring = arrow.get(float(r[3])).shift(hours=-5).humanize() # ugh the timezone issue is tricky!
        if abs(time.time() - float(r[3])) < gap:
            feeds[feeddata[1]].append(tuple([r[4], timestring, r[1], r[5], r[3]])) # keep the epoch time for sorting
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

if __name__ == "__main__":
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
    feeds, settings = buildSettings(cursor) 
    x = frame(settings)
    # do some database maintenance
    # look at the feeds already parsed above
    updates = list()
    deletes = list()
    for f in [_ for _ in feeds if len(feeds[_])>0]:
        sortedlist = sorted(feeds[f], key=lambda x: x[4])
        lastupdate = sortedlist[-1][-1]
#        log.append(f + ' last updated ' + arrow.get(lastupdate).shift(hours=-5).humanize())
        updates.append(tuple([lastupdate, 'True', f]))
        if len(sortedlist) > 40:
            for entry in sortedlist[:len(sortedlist)-39]:
                deletes.append(tuple([entry[0], entry[4]]))
    cursor.executemany('DELETE FROM entries WHERE headline=? AND date=?', deletes)
    log.append('Purged ' + str(len(deletes)) + ' entries.')
    cursor.executemany('UPDATE feeds SET newest_feed=?, success=? WHERE feed_name=?', updates)
    conn.commit()    

    cursor.execute('SELECT feed_name, newest_feed FROM feeds ORDER BY newest_feed')
    results = cursor.fetchall()
    feedsummary = ['\n\nSummary of feeds in the database after latest check:\n']
    for r in reversed(results):
        if r[1]:
            feedsummary.append(r[0] + ' last updated ' + arrow.get(r[1]).to('US/Eastern').humanize() + '.') # TIME ZONE INFO HAS TO BE USER CONFIG'D
    conn.close()
    with open('index.html', 'w', encoding='utf-8') as fh:
        fh.write(x)
    finallog = alerts + feedsummary + log + setuplog
    with open('logs/log.txt', 'w') as fh:
        fh.write('\n'.join(finallog))
    now = arrow.utcnow()
    logpath = os.path.join('logs', str(now.year), str(now.month), str(now.day))
    os.makedirs(logpath, exist_ok=True)
    with open(os.path.join(logpath, 'full.log'), 'a') as fh:
        fh.write('\n\n' + '-' * 12 + arrow.utcnow().format() + '-' * 12 + '\n\n' + '\n'.join(finallog))

