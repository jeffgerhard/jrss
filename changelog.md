# Changelog

## [0.1.5] - 2019-02-07

### Changed
* Stopped searching for favicons over and over (sorry, non-icon-having websites!)
* Minor bugfix on data cleanup of incoming XML
* Minor stylesheet updates
* Revised the delete-old-function functionality and added the SQL VACUUM command which I was not aware even existed?

## [0.1.4] - 2019-01-19

### Changed
* Tweaked some style details, including line breaks in tooltips, [unescaping html](https://docs.python.org/3/library/html.html#html.unescape), and capitalization of authors in feeds

## [0.1.3] - 2019-01-18

### Added
* Included feed authors by default, in database and page display
* Database size info to logs

### Changed
* Tweaked method of stripping out HTML tags, using `bleach` module to allow innocuous tags in feed titles
* Changed default display to just the past 30ish hours; still need to make this easier to configure

## [0.1.2] - 2019-01-12

### Changed
* Removed html in summaries
* Small layout, bug, and css fixes

## [0.1.1] - 2019-01-10

### Added
* Awareness of [ETag and Last-Modified Headers](https://pythonhosted.org/feedparser/http-etag.html) and [HTTP Redirects](https://pythonhosted.org/feedparser/http-redirect.html)
* jrss user-agent string
* A minimalist refresh button
* HTML `meta` referrer and robots tags
* Some minor buxfixes and code updates
* This changelog

### Changed
* Shrank the size of demo image
* Some updates and corrections to the README