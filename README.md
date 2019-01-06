# jrss feedreader
## a modern feedreader in the vein of classic web services like My Yahoo! and iGoogle
### v. 0.1.0

This is a Python program to build a portal-style feed reader. There are many viewers for keeping up on feeds in the spirit of Google Reader, but I have never been able to fully replace the casual viewing style of My Yahoo! circa 2004. I use this as a method of looking at headlines on my phone.

This program generates a static page that supports user-defined feeds in categories.

![demo image](demo.jpg)

### Set up:

This is envisioned as something to run on a local server; however, it will work on a local machine as well. 

There are a bunch of required python modules; they are listed in the requirements.txt file. You can use this like so:

```$ pip install -r requirements.txt```

It optionally will use a duckduckgo module available [here](https://github.com/jeffgerhard/duckduckgo-python3), but you can't install this from `pip`.

The repo includes a demo `feeds/feeds.csv` file that you can use to try this out. There are four columns in this csv, for a feed name, feed category, feed url, and (not-yet-implemented) feed filter.

The feeds are parsed and saved in a sqlite database, and an index.html file is generated, suitable for moving and deplying on a server wherever you might like it.

_This is a beta version_ and needs a lot of code cleanup! But you can run it as `jpage.py` after all is set up.

### Future features

This is not entirely finished. Future features include:

* Widgets (like weather or breaking news alerts or other items to put at top of pages)
* Feed filter implementation
* CSS adjustments and cleanup
* Better management utilities (i.e., user-initiated database rebuild.)
* Special categories
* Intelligent management of deprecated and error-riddle feeds; assessment of feed frequency.




