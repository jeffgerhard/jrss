import logging
import sqlite3
import os
import requests
import favicon
# import json
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import feedparser
from dateutil import parser
from datetime import datetime
import time
import arrow
import sys
import re
import duckduckgo
import html
from bleach import Cleaner
import re
from jrss import __version__
from jrss.htmlbuild.htmlbuild import frame


feedparser.USER_AGENT = f'jrss/{__version__} +https://github.com/jeffgerhard/jrss'
DBFILE = 'src/jrss/jrss.db'
FEEDCSV = 'config/feeds/feeds.csv'
LOCAL_TIMEZONE = 'US/Eastern'  # could put this in a yaml or something

# create logger
logger = logging.getLogger('feedreader')
logger.setLevel(logging.DEBUG)

# create file handler that includes even DEBUG logs
fh = logging.FileHandler('output/logs/jrss.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)


cleaner = Cleaner(tags=['i', 'em', 'b', 'br', 'p', 'strong', 'code', 'abbr'],
                  attributes={'*': ['style'] },
                  css_sanitizer=['color', 'background-color', 'font', 'font-family', 
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
        feed_name char(100) NOT NULL,
        link char(100) NOT NULL,
        category char(100) NOT NULL,
        filters char(500),
        success char(5),
        newest_feed char(50),
        etag char(50),
        lastmod char(100),
        timezone char(50),
        csv_link char(100) NOT NULL)
    """)
    statements.append("""CREATE TABLE icons
        (table_id INTEGER PRIMARY KEY,
        icon BLOB,
        feed_id INTEGER NOT NULL,
        attempted char(23))
        
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
    cursor = conn.cursor()        
    cursor.execute('INSERT INTO schema (version) VALUES (?)', (__version__,))
    conn.commit()
    cursor.close()
    logger.info('Generated database')
    return conn

def populate(conn):
    cursor = conn.cursor()
    # newfeeds = False
    csv_feeds = list()
    with open(FEEDCSV, 'r') as fh:
        feeds = [_ for _ in fh.read().splitlines() if _]
    cursor.execute('SELECT feed_name, id, csv_link, category FROM feeds')
    results = cursor.fetchall()  
    updates = list()
    for f in feeds:
        found = False
        flist = f.split(',')
        csv_feeds.append((flist[0], flist[1], flist[2]))  # name, category, url
        for r in results:
            if r[0] == flist[0] and r[2] == flist[2] and r[3] == flist[1]:
                logger.info('found ' + str(flist[0]) + ' in db.')
#                print('found', flist[0], 'in db.')
                found = True
        if found is False:
            flist.append(flist[2])
            updates.append(tuple(flist))
            # newfeeds = True
 #           print('Adding', flist[0], 'to db.')
            logger.info('Adding ' + str(flist[0]) + ' to db.')
    # try to clear out old feeds in feeds table
    for r in results:
        if (r[0], r[3], r[2]) not in csv_feeds: 
            t = (r[0], r[3], r[2])
            print(t) # name, url (which?), category
            logger.warning(f'{t} not found in csv. Deleting')
            cursor.execute('DELETE FROM feeds where id=?', (r[1],))
    # print('csv_feeds:')
    # print(csv_feeds)
    if len(updates) > 0:
        cursor.executemany('INSERT INTO feeds (feed_name, category, link, filters, csv_link) VALUES (?, ?, ?, ?, ?)', updates)
    # cursor.execute('INSERT INTO schema (version) VALUES (?)', (__version__,))
    # commenting out; this was redundant
    conn.commit()
    return conn

def getIcon(conn):
    cursor = conn.cursor()
    cursor.execute('''SELECT id, feed_name, link,
                        icon, attempted
                      FROM feeds
                    LEFT JOIN icons
                    ON
                    feeds.id = icons.feed_id ''')
    feeds = cursor.fetchall()
    for feed in feeds:
        # print(feed)
        logger.debug(f'Checking icon for feed: {str(feed[0])}. {str(feed[1])} {str(feed[2])})')
        iconurl = None
        if feed[3]:
            logger.debug(f'Icon already saved in db for {feed[2]}')
            continue
        elif feed[4]:
            logger.debug(f'Icon search was attempted recently ({feed[4]})')
            continue
        uri = feed[2]
        link = 'http://' + uri.split('//')[1].split('/')[0] + '/'
        
        if 'feedburner' in uri: 
            r = duckduckgo.query(feed[1])
            if r.type == 'answer':
                if r.results[0]:
                    logger.debug(f'tryin to track icon for {r.results[0].url}')
                    link = r.results[0].url        
                else:
                    logger.debug(f'No icon found for {feed[2]}')
                    utc = arrow.utcnow()
                    local = utc.to('US/Eastern')
                    update = (local.format(), feed[0])
                    cursor.execute('''INSERT INTO icons(attempted, feed_id)
                            VALUES (?, ?)''', update)
                    conn.commit()

        try:
            icons = favicon.get(link, timeout=5)
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
                try:
                    image = Image.open(BytesIO(img_data))
                except UnidentifiedImageError:
                    logger.debug(f'No icon found for {link}')
                    continue
                image.thumbnail((40, 80))
                imgByteArr = BytesIO()  # this stuff via https://stackoverflow.com/a/33117447
                image.save(imgByteArr, format='PNG')
                imgByteArr = imgByteArr.getvalue()
                utc = arrow.utcnow()
                local = utc.to('US/Eastern')

                # update = (imgByteArr, feed[0])
                update = (local.format(), imgByteArr, feed[0])
                cursor.execute('''INSERT INTO icons(attempted, icon, feed_id)
                            VALUES (?, ?, ?)''', update)
                conn.commit()
                logger.info(f'Added icon for {link}')
        else:
            utc = arrow.utcnow()
            local = utc.to('US/Eastern')
            update = (local.format(), feed[0])
            cursor.execute('''INSERT INTO icons(attempted, feed_id)
                            VALUES (?, ?)''', update)
            conn.commit()

    cursor.close()
    return conn

def checkFeeds(conn):
    cursor = conn.cursor()
    logger.info('Checking feeds...')
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
        try:
            _ = d.status
        except AttributeError:
            logger.warning(f'row[1] HAS A MAJOR ERROR IN FEED')
            # alerts.append('\n *** ' + row[1] + ' HAS A MAJOR ERROR IN FEED')
            d.status = 0
            checkentries = False
        if d.status == 304:
            logger.info('Unmodified. (Etag or modified date match.)')
            # note += '\n\tUnmodified. (Etag or modified date match.)'
            checkentries = False
        elif d.status == 302:
            logger.info(f'{row[1]} was temporarily redirected based on a 302 status.')
            # note += '\n\t' + row[1] + ' was temporarily redirected based on a 302 status.'
        elif d.status == 301:
            logger.warning(f'{link} HAS A 301 PERMENANENT REDIRECT')
            logger.info(f'Updated to {d.href}')
            # alerts.append('\n * ' + link + ' HAS A 301 PERMENANENT REDIRECT\n\tUpdated to ' + d.href)
#            print('\n\t* trying to update link in database for', link)
            cursor.execute('UPDATE feeds SET link=? WHERE id=?', (d.href, row[0],))
        elif d.status == 401:
            logger.warning(f'{row[1]} HAS A 410 GONE STATUS (ADD CODE TO TRACK THIS AND LATER DELETE THE FEED????')
            # alerts.append('\n *** ' + row[1] + ' HAS A 410 GONE STATUS (ADD CODE TO TRACK THIS AND LATER DELETE THE FEED????)')
            checkentries = False
        if 'etag' in d:
            if row[2] != d.etag:
                cursor.execute('UPDATE feeds SET etag=? WHERE id=?', (d.etag, row[0],))
        if 'modified' in d:
            if row[3] != d.modified:
                cursor.execute('UPDATE feeds SET lastmod=? WHERE id=?', (d.modified, row[0],))
        if checkentries is True:
            if d.entries:
                note = 'Found feed (title: ' + d.feed.title
                note += ') with ' + str(len(d.entries)) + ' entries'
                logger.info(note)
                existing_entries = 0
                new_entries = 0
                repeated_entries = 0
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
                    else:
                        update = True
                        t = _.title
                        cursor.execute('SELECT headline FROM entries WHERE entry_uri=?', (t,))
                        results = cursor.fetchone()
                        if results:
                            update = False
                            repeated_entries += 1                        
                    if update is True:
                        new_entries += 1
                        epochdate = 0
                        feed_id = row[0]
                        # if 'published_parsed' in _:
                        if 'published' in _ and _.published:
                            # try:
                                # epochdate = time.mktime(_.published_parsed)
                            dt = parser.parse(_.published)
                            # epochdate = _.published_parsed.timestamp()
                            epochdate = dt.timestamp()
                                # THIS IS WHERE MY TIMES ARE MESSED UP
                                # SWITCH THIS TO DATETIME MODULE
                            # except:
                            #     pass
                        # elif 'updated_parsed' in _:
                        elif 'updated' in _ and _.updated:
                            # try:
                                # epochdate = time.mktime(_.updated_parsed)
                            dt = parser.parse(_.updated)
                                # epochdate = _.updated_parsed.timestamp()
                            epochdate = dt.timestamp()
                            # except:
                            #     pass
                        else:
                            logger.info('Feed without date found')
                        if 'summary' in _:
                            summary = html.unescape(_.summary)
                            summary = summary.replace('\xa0', ' ').replace('<p>', '\n\n<p>')
                            summary = summary.replace('<li>', '\n  • <li>')
                            summary = re.sub(re.compile('<.*?>'), '', summary)[:400]
                            while '\n\n\n' in summary:
                                summary = summary.replace('\n\n\n','\n\n')
                            summary = summary.strip()
                            #summary = cleaner.clean(_.summary[:500])
#                        elif 'authors' in _:
#                            author = cleaner.clean(', '.join(_.authors)[:400])
                        else: 
                            summary = None
                        if 'title' in _:
                            title = cleaner.clean(html.unescape(_.title))[:399]
                        else:
                            title  = None
                        if 'author' in _:
                            author = cleaner.clean(html.unescape(_.author))[:400]
                        else:
                            author = None
                        link = None
                        try:
                            link = _.link
                        except:
                            link = '[no link]'
                        updater = [link, guid, epochdate, title, summary, feed_id, author]
                        updates.append(tuple(updater))
                if new_entries > 0:
                    note = str(new_entries) + ' added to db. '
                    logger.info(note)
                if existing_entries > 0:
                    note = str(existing_entries) + ' were already in the db.'                
                    logger.debug(note)
                if repeated_entries > 0:
                    note = str(repeated_entries) + ' were dupes of other database entries.'
                    logger.debug(note)
            else:
                logger.warning(f'FEED FAILED: couldn\'t parse {row[1]}')
                # alerts.append('\n* FAILED FEED: couldn\'t parse ' + row[1] + '.')
        # log.append(note)
    if len(updates) > 0:
        cursor.executemany('INSERT INTO entries (entry_uri, guid, date, headline, summary, feed_id, authors) VALUES (?, ?, ?, ?, ?, ?, ?)', updates)
        # return alerts, log, updates
        conn.commit()
        cursor.close()
        return conn


def buildSettings(conn, gap=700000):
    settings = dict()
    sections = dict()
    feeds = dict()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entries')
    rows = cursor.fetchall()
    for r in rows:
        entryfeedid = r[6]
        cursor.execute('''SELECT icon, feed_name, category, timezone
        FROM feeds 
        left join icons
        on feeds.id = icons.feed_id
        WHERE id=?
        ''', (entryfeedid,))
        feeddata = cursor.fetchone()
        feed_name = feeddata[1]
        if feed_name not in feeds:
            feeds[feed_name] = list()  # this is just the old way i made dictionaries
        # if feeddata[3]:

        timestring = arrow.get(float(r[3]), tzinfo='utc').to('US/Eastern').humanize() # NEED TO MAKE THIS CONFIGURABLE
        #timestring = arrow.get(float(r[3])).shift(hours=-5).humanize() # ugh the timezone issue is tricky!
        if abs(time.time() - float(r[3])) < gap:
            feeds[feeddata[1]].append(tuple([r[4], timestring, r[1], r[5], r[3], r[7]])) # keep the epoch time for sorting
    for f in [_ for _ in feeds if len(feeds[_])>0]:
        cursor.execute('''SELECT icon, category FROM 
                    feeds left join icons
                    on feeds.id = icons.feed_id 
                    WHERE feed_name=?''', (f,))
        feeddata = cursor.fetchone()
        sortedfeed = sorted(feeds[f], key=lambda x: x[4], reverse=True)
        # skip feeds that haven't been updated in a while...
        if abs(time.time() - float(sortedfeed[0][4])) < gap: # around 8 days
            if feeddata[1] not in sections:
                sections[feeddata[1]] = list()
            sections[feeddata[1]].append({f: {'entries': sortedfeed, 'icon': feeddata[0]}})
    settings['version'] = __version__
    settings['sections'] = sections
    logger.debug('Compiling feeds for display')
    # print(feeds)
    return conn, feeds, settings


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


def dbsize():
    return humanbytes(os.stat(DBFILE).st_size)

def testsetup():
    if not os.path.exists(FEEDCSV):
        logger.exception('Feeds file not found')
        raise UserWarning('There are no feeds! See setup documentation for help setting up and a demo.')
    for _ in ['output/html', 'output/logs']:
        os.makedirs(_, exist_ok=True)
    logger.debug('Config verified')


def testdb():  # check db config and 
    sz = dbsize()
    logger.info(f'Beginning database size: {sz}')
    conn = sqlite3.connect(DBFILE) 
    cursor = conn.cursor()   
    try:
        cursor.execute('SELECT version FROM schema')
        results = cursor.fetchone()
        if str(results[0]) == str(__version__):
            logger.debug('DB file set up properly')
            cursor.close()
            return conn
        else:
            logger.info('DB version outdated')
    except:
        logger.info('Database does not contain version')
    cursor.close()
    conn.close()
    os.remove(DBFILE)
    logger.info('Deleting old db')
    conn = sqlite3.connect(DBFILE) 
    conn = schema(conn)  # set up table
    logger.info('Rebuilt database from scratch')
    return conn

def datefix(d: str):
    ''' prepare datestrings for arrow by lopping off decimals '''
    pattern = r'\.(\d+)'
    if re.search(pattern, d):
        return int(d[:re.search(pattern, d).span()[0]])
    else:
        try:
            return int(d)
        except ValueError:
            return d

def cleanup(conn, feeds):
    updates = list()
    deletes = list()
    for f in [_ for _ in feeds if len(feeds[_])>0]:
        sortedlist = sorted(feeds[f], key=lambda x: x[4])
        lastupdate = datefix(sortedlist[-1][4])
        logger.info(f + ' last updated ' + arrow.get(lastupdate).shift(hours=-5).humanize())
        updates.append(tuple([lastupdate, 'True', f]))
    cursor = conn.cursor()
    cursor.executemany('UPDATE feeds SET newest_feed=?, success=? WHERE feed_name=?', updates)
    for f in range(0, len(feeds) + 20):
        cursor.execute('SELECT id, entry_uri, date FROM entries WHERE feed_id=?', (f,))
        rows = cursor.fetchall()
        if len(rows) > 40:
            s = sorted(rows, key=lambda x: x[2])
            for _ in s[:39]:
                deletes.append(_[0])  # just m ake a list of db ids to delete
    if deletes:
        for d in deletes:
            cursor.execute('DELETE FROM entries WHERE id=?', (d,))
        logger.info('Purged ' + str(len(deletes)) + ' entries.')
    
    conn.commit()    
    conn.execute('VACUUM')
    logger.info('Final database size: ' + dbsize())
    cursor.execute('SELECT feed_name, newest_feed FROM feeds ORDER BY newest_feed')
    results = cursor.fetchall()
    feedsummary = ['\n\nSummary of feeds in the database after latest check:\n']
    for r in reversed(results):
        # print(r)
        if r[1] and str(r[1]) and str(r[1]) != '':
            # check for any ".0" type things in strings
            # pattern = r'\.(\d+)'
            # if re.search(pattern, r[1]):
            #     dd = int(r[1][:re.search(pattern, r[1]).span()[0]])
            # else:
            #     dd = r[1]
            feedsummary.append('\t' + r[0] + ' last updated ' + arrow.get((datefix(r[1]))).to('US/Eastern').humanize() + '.') # TIME ZONE INFO HAS TO BE USER CONFIG'D
    logger.info('\n'.join(feedsummary))
    cursor.close()
    return conn
    
def timezone_guess(conn):
    ''' try to discern if any feeds are coming from UTC or other timezone '''
    cursor = conn.cursor()
    cursor.execute('select id, newest_feed, lastmod, timezone, feed_name from feeds')
    results = cursor.fetchall()
    for r in results:
        if r[1]:
            now = time.time()
            if float(r[1]) > now:
                logger.info(f'Feed {r[0]} {r[4]} seems to have a newer timestamp than now, updating the tz?')
                # cursor.execute('UPDATE feeds SET timezone=? where id=?', ('UTC', r[0]))
        

def main():
    logger.info('Launching feedreader module')
    testsetup()
    logger.info(f'jrss running is version {__version__}')
    conn = testdb()
    conn = populate(conn)
    conn = getIcon(conn)
    conn = checkFeeds(conn)
    conn, feeds, settings = buildSettings(conn, gap=108000) 
    x = frame(settings)
    with open('output/html/index.html', 'w', encoding='utf-8') as fh:
        fh.write(x)

    conn = cleanup(conn, feeds)
    timezone_guess(conn)

    # Still to do:
    #  - rotate/clean logs
    #  - clean out unused icons
    #  - refresh icons periodically
    #  - cleanup of timezones (move future dates to past for one thing, and make tz configurable)

if __name__ == '__main__':
    main()
