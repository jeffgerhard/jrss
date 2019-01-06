# jrss feedreader
## a modern feedreader in the vein of classic web services like My Yahoo! and iGoogle
### v. 0.1.0

This is a Python program to build a portal-style feed reader. There are many viewers for keeping up on feeds in the spirit of Google Reader, but I have never been able to fully replace the casual viewing style of My Yahoo! circa 2004. I use this as a method of looking at headlines on my phone.

This program generates a static page that supports user-defined feeds in categories.

![demo image](demo.jpg)

### Set up:

This is envisioned as something to run on a local server; however, it will work on a local machine as well. 

This is Python 3 script only.

There are a bunch of required python modules; they are listed in the requirements.txt file. You can use the requirements file like so:

```$ pip install -r requirements.txt```

The program will optionally use a duckduckgo module available [here](https://github.com/jeffgerhard/duckduckgo-python3), but you can't install this from `pip`.

The repo includes a demo `feeds/feeds-demo.csv` file that has some sample RSS feeds in it. Rename or copy this file as `feeds/feeds.csv` and you can edit it by adding whatever other feeds you want. There are four columns in this csv: feed name, feed category, feed url, and (not-yet-implemented) feed filter.

The feeds are parsed and entries are saved in a sqlite database, and an index.html file is generated, suitable for moving and deplying on a server wherever you might like it. The program attempts to find and include favicons for the feeds (this is where that DuckDuckGo module might help for those that are hard to find).

_This is a beta version_ and needs a lot of code cleanup! But you can run it as `jpage.py` after all is set up.

### Running as cron job, etc.

I have set up a shell script on my server that looks basically like this:

```
#!/bin/shell
python /srv/repos/jrss/jpage.py
cp /srv/repos/jrss/index.html /var/www/html/
cp -r /srv/repos/jrss/logs /var/www/html/
```

Make sure to `chmod` this script (per [these instructions](https://askubuntu.com/questions/350861/how-to-set-a-cron-job-to-run-a-shell-script).



### Future features

This is not entirely finished. Future features include:

* Widgets (like weather or breaking news alerts or other items to put at top of pages)
* Feed filter implementation
* CSS adjustments and cleanup
* Better management utilities (i.e., user-initiated database rebuild.)
* Special categories
* Intelligent management of deprecated and error-riddle feeds; assessment of feed frequency.
* User configuration of more features (like time zone, number of feed entries to display, age of entries to display, etc.)


