###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James Vega
# Copyright (c) 2010-2013, Jeff Mahoney
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import re

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import SingletonBrowser
from pysqlite2 import dbapi2 as sqlite3
import os
import urllib2
import mechanize
import traceback
import getpass
from urllib import urlencode
from bs4 import BeautifulSoup
import gzip
from optparse import OptionParser
import HTMLParser
import SingletonBrowser
import datetime
import sys

class SqlShrunkenUrlDB(object):
    def __init__(self, filename):
        filename = filename.replace('.db', '.Info.db')
        self.filename = filename

class CdbShrunkenUrlDB(object):
    def __init__(self, filename):
        self.tinyDb = conf.supybot.databases.types.cdb.connect(
            filename.replace('.db', '.Tiny.db'))
        self.lnDb = conf.supybot.databases.types.cdb.connect(
            filename.replace('.db', '.Ln.db'))
        self.dnbDb = conf.supybot.databases.types.cdb.connect(
            filename.replace('.db', '.Dnb.db'))

    def getTiny(self, url):
        return self.tinyDb[url]

    def setTiny(self, url, tinyurl):
        self.tinyDb[url] = tinyurl

    def getLn(self, url):
        return self.lnDb[url]

    def setLn(self, url, lnurl):
        self.lnDb[url] = lnurl

    def getDnb(self, url):
        return self.dnbDb[url]

    def setDnb(self, url, shurl):
        self.dnbDb[url] = shurl

    def close(self):
        self.tinyDb.close()
        self.lnDb.close()

    def flush(self):
        self.tinyDb.flush()
        self.lnDb.flush()

ShrunkenUrlDB = plugins.DB('Snarfer', {'cdb': CdbShrunkenUrlDB })
ShrunkenUrlSDB = plugins.DB('Snarfer', {'sqlite' : SqlShrunkenUrlDB})

ipAddressRegex = re.compile(r"^((((([0-9]{1,3})\.){3})([0-9]{1,3}))((\/[^\s]+)|))$")
httpUrlRegex = re.compile(r"(https?://[^\]>\s]+)", re.I)
class Snarfer(callbacks.PluginRegexp):
    regexps = ['shrinkSnarfer']
    def __init__(self, irc):
        self.__parent = super(Snarfer, self)
        self.__parent.__init__(irc)
        self.db = ShrunkenUrlDB()
        self.infoDb = ShrunkenUrlSDB()
        self.browser = SingletonBrowser.SingletonBrowser()
        print "Snarfer initializing."

    def reload(self):
        reload(info)

    def die(self):
        self.db.close()

    def callCommand(self, command, irc, msg, *args, **kwargs):
        try:
            self.__parent.callCommand(command, irc, msg, *args, **kwargs)
        except utils.web.Error, e:
            irc.error(str(e))

    def interpolate_url(self, url):
        if re.search(r"^(([0-9]+)\.)+(|[0-9]+)$", url):
            m = ipAddressRegex.search(url)
            if not m:
                return None

            ip = m.group(2)
            array = ip.split('.', 4)
            if int(array[0]) == 0:
                return None

            for num in array:
                if int(num) > 255:
                    return None
        return "http://" + url

    def shrinkSnarfer(self, irc, msg, match):
        r"(^|\s+)(([\|\$\!\~\^]+)|)(((([\w\-]+\.)+)([\w\-]+))(((/[\w\-\.%\(\)~]*)+)+|\s+|[\!\?\.,;]+|$)|https?://[^\]>\s]*)"
#        r".*(\s+|\!|\~\!|\||^|\^)(((([\w\-]+\.)+)([\w\-]+))(((/[\w\-\.%\(\)~]*)+)+|\s+|[\!\?\.,;]+|$)|https?://[^\]>\s]*).*"
        channel = msg.args[0]
        nick = msg.nick

        self.log.info("shrinkSnarfer called")

        if not irc.isChannel(channel):
            self.log.info("wrong channel")
            return
        if self.registryValue('shrinkSnarfer', channel):
            url = match.group(4)
            r = self.registryValue('nonSnarfingRegexp', channel)
            if r and r.search(url) is not None:
                self.log.debug('Matched nonSnarfingRegexp: %u', url)
                return
            minlen = self.registryValue('minimumLength', channel)
            cmd = self.registryValue('default', channel)
	    ext_info = self.registryValue('extendedInfo', channel)
            interpolate = self.registryValue('interpolate', channel)
            if len(url) >= minlen:
                shorturl = None

                while url[-1:] == '/':
                    url = url[:-1]
                interpolated = False
                if not httpUrlRegex.search(url):
                    if interpolate:
                        url = url.strip()
                        url = self.interpolate_url(url)
                        if url is None:
                            return
                        interpolated = True
                    else:
                        return

                info_data = None
		if ext_info:
                    try:
                        info_data = SnarferInfo(self.infoDb, self.browser,
                                                nick, channel, url, self.log)
                        if not info_data.valid:
                                info_data.fetch()

                        if not info_data.valid:
                            del info_data
                            info_data = None
                    except urllib2.URLError, e:
                        if not interpolated:
                            m = irc.reply(str(e), prefixNick=False)
                        return

                mods = match.group(2)
                nsfw = 0
                private = False
                if mods:
                    if '$' in mods:
                        nsfw |= 4
                    if '!' in mods:
                        nsfw |= 2
                    elif '~' in mods:
                        nsfw |= 1
                    if '^' in mods:
                        private = True

                try:
                    if cmd == 'tiny':
                        shorturl = self._getTinyUrl(url)
                    elif cmd == 'dnb':
                        shorturl = self._getDnbUrl(url)
                    elif cmd == 'ln':
                        (shorturl, _) = self._getLnUrl(url)
                    if shorturl is None:
                        self.log.info('Couldn\'t get shorturl for %u', url)
                        shorturl = "ln-s.net refused shortlink"
                except urllib2.URLError, e:
                    if not interpolated:
                        m = irc.reply(str(e), prefixNick=False)


                if not ext_info:
                    if self.registryValue('shrinkSnarfer.showDomain', channel):
                        domain = ' (at %s)' % utils.web.getDomain(url)
                    else:
                        domain = ''
                    if self.registryValue('bold'):
                        s = format('%u%s', ircutils.bold(shorturl), domain)
                    else:
                        s = format('%u%s', shorturl, domain)
                    m = irc.reply(s, prefixNick=False)
                    m.tag('shrunken')

                if info_data:
                    if not info_data.cached:
                        info_data.nsfw = nsfw
                        info_data.shorturl = shorturl
                        info_data.add_url()
                    else:
                        new_nsfw = info_data.nsfw
                        if (nsfw & 2) and (info_data.nsfw & 1):
                            new_nsfw |= 2
                            new_nsfw &= ~1

                        new_nsfw |= (nsfw & ~3)
                        if info_data.nsfw != new_nsfw:
                            info_data.nsfw = new_nsfw
                            info_data.set_url_nsfw(new_nsfw)
                    info_str = unicode(info_data)
                    if 0 and len(info_str) + len(irc.nick) > 70:
                        for line in info_str.split("\n"):
                            m = irc.reply(line, prefixNick=False)
                            m.tag('shrunken')
                    else:
                        info_str = info_str.replace("\n", " ")
                        if info_str != "":
                            m = irc.reply(info_str, prefixNick=False)
                    msg = unicode(info_data)
                    self.log.info(msg)

    shrinkSnarfer = urlSnarfer(shrinkSnarfer)

    def _getDnbUrl(self, url):
        url = utils.web.urlquote(url)
        try:
            return self.db.getDnb(url)
        except KeyError:
            text = utils.web.getUrl('http://dnb.us/surl-api.php?url=' + url)
            dnburl = text.strip()
            self.db.setDnb(url, dnburl)
            return dnburl

    def _getLnUrl(self, url):
        url = utils.web.urlquote(url)
        try:
            return (self.db.getLn(url), '200')
        except KeyError:
            text = utils.web.getUrl('http://ln-s.net/home/api.jsp?url=' + url)
            (code, lnurl) = text.split(None, 1)
            lnurl = lnurl.strip()
            if code == '200':
                self.db.setLn(url, lnurl)
            else:
                lnurl = None
            return (lnurl, code)

    _tinyRe = re.compile(r'<blockquote><b>(http://tinyurl\.com/\w+)</b>')
    def _getTinyUrl(self, url):
        try:
            return self.db.getTiny(url)
        except KeyError:
            s = utils.web.getUrl('http://tinyurl.com/create.php?url=' + url)
            m = self._tinyRe.search(s)
            if m is None:
                tinyurl = None
            else:
                tinyurl = m.group(1)
                self.db.setTiny(url, tinyurl)
            return tinyurl

Class = Snarfer
def get_encoding(resp):
    headers = resp.info()
    if 'Content-type' in headers:
        content_type = headers['Content-type'].lower()
        m = re.search('charset=(\S+)', content_type)
        if m:
            return m.group(1)

    return None

#def to_unicode(resp, text):
#    headers = resp.info()
#    if 'Content-type' in headers:
#        content_type = headers['Content-type'].lower()
#        m = re.search('charset=(\S+)', content_type)
#        if m:
#            text = text.decode(m.group(1)).encode('utf-8')
#            print "translated from %s: %s" % (m.group(1), text)
#        else:
#            print "content type %s" % content_type
#    else:
#        print "skipped %s" % text
#
#    return text

class InvalidURLException(Exception):
    pass

class SnarferFailure(Exception):
    pass

helpers = []
class UrlHelper(object):
    def __init__(self):
        self.clear_title = False
    def match(self, url, type):
        return False

class ImgUrUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True
        self.url_regex = re.compile("imgur.com/(\S+)\....")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        m = self.url_regex.search(url)
        url = "http://imgur.com/gallery/%s" % (m.group(1))

        r = snarfer.open_url(url)
        s = BeautifulSoup(r.read())
        title = s.title.string
        if title is not None:
            title = " ".join(title.split())

        return title

class TwitterUrlHelper(UrlHelper):
    def __init__(self):
        UrlHelper.__init__(self)
        self.clear_title = True
        self.url_regex = re.compile("twitter.com/.*/status")

    def match(self, url):
        if self.url_regex.search(url):
            return True
        return False

    def fetch(self, snarfer, url, resp):
        url = re.sub("/#!", "", url)
        url = re.sub("^https", "http", url)
        resp = snarfer.open_url(url)
        s = BeautifulSoup(resp.read())
        p = s.findAll('p', 'tweet-text')
        text = None
        if p:
            for part in p[0].contents:
                if text is None:
                    text = ""
                text += str(part)
            text = re.sub(r'<[^>]*?>', '', text)

        #print html

        p = s.findAll('strong', 'fullname')
        print p
        if p:
            name = p[0].contents[0]
        if text and name:
            desc = "%s: %s" % (str(name), text.strip())
            return desc
        return None

helpers.append(ImgUrUrlHelper())
helpers.append(TwitterUrlHelper())
def find_url_helper(url):
    for helper in helpers:
        if helper.match(url) is True:
            return helper
    return None

selfRefRegex = re.compile(r"http://(ln-s.net|dnb.us|tinyurl.com)/([A-Za-z0-9]+)")
class SnarferInfo():
    def __init__(self, db, browser, nick, channel, url, log, update_count=True):
	self.db = db
	self.url = url
	self.browser = browser
	self.valid = False
	self.cached = False
	self.log = log

	self.nick = nick
	self.channel = channel
	self.count = None
	self.first_seen = None
	self.title = None
	self.now = None
	self.nsfw = None
	self.type = None
	self.description = None
	self.shorturl = None

	self.log.info("Loaded info")

	m = selfRefRegex.search(url)
	if m is not None:
	    self.get_by_url(url, True)

	if not self.valid:
	    self.get_by_url(url, False)

	if self.valid and update_count:
	    self.increment_count()

        if self.valid:
            self.cached = True

    def pretty_title(self):
        title = self.title.strip()
        if title is None:
            title = u""
        else:
            title += u""
        if self.nsfw > 0:
            title += u" ("

            if self.nsfw & 2:
                title += u"NSFW"
            elif self.nsfw & 1:
                title += "u~NSFW"

            if self.nsfw & 4:
                if self.nsfw & 3:
                    title += ", "
                title += "SPOILERS"
            title += u")"
        return title

    def tostring(self, with_description=True):
	if not self.valid:
	    return "<invalid info>"
	desc = u""
        title = self.pretty_title()
	if title:
	    desc += "(%s)" % title.replace("\n", "")
	elif self.description:
	    desc += "(%s)" % self.description.replace("\n", "")

	if self.count > 1:
	    if desc != "":
		desc += " "

	    desc += "[%dx, %s, %s] " % (self.count, self.nick, self.timeAgo())

        if self.shorturl:
            s = u""
            s += self.shorturl
            if with_description:
                s += "\n" + desc
        else:
            return desc

	return s

    def __repr_(self):
	return self.tostring(True)
    def __str__(self):
	return self.tostring(True)

    def fill_from_row(self, row):
	self.url = row[0]
	self.nick = row[1]
	self.channel = row[2]
	self.count = int(row[3])
	self.first_seen = row[4] #time.gmtime(row[4])
	self.title = row[5]
	self.now = row[6]
	self.nsfw = row[7]
	self.type = row[8]
	self.description = row[9]
	self.shorturl = row[10]

	self.valid = True

    def get_by_url(self, url, short=False):
	q  = r"SELECT url, nick, channel, count, first_seen as 'ts [timestamp]', "
	q += r"title, DATETIME(CURRENT_TIMESTAMP, 'unixepoch'), nsfw, type, description, shorturl "
	q += r"FROM url WHERE channel = ? AND "
	if short:
	    q += "shorturl = ?"
	else:
	    q += "url = ?"

        db = self.connect()

        try:
            cursor = db.cursor()
            cursor.execute(q, [self.channel, url])
            row = cursor.fetchone()
            if row:
                self.fill_from_row(row)
            db.close()
        except sqlite3.OperationalError, e:
            db.close()
            raise e

    def connect(self):
        filename = self.db.filename
        if os.path.exists(filename):
            db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_COLNAMES)
        else:
            db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_COLNAMES)
            cursor = db.cursor()
            q = r"CREATE TABLE url ( url TEXT, shorturl TEXT, nick TEXT, first_seen TIMESTAMP DEFAULT (DATETIME('now')), title TEXT, nsfw INT, type TEXT, description TEXT, channel TEXT, count INT DEFAULT 0 )"
            cursor.execute(q)
            db.commit()
        return db

    def do_update(self, query, args):
        db = self.connect()
        try:
            cursor = db.cursor()
            cursor.execute(query, args)
            db.commit()
        except Exception, e:
            print "%s: %s" % (query, e)
        db.close()

    def increment_count(self):
	q = r"UPDATE url SET count = count + 1 WHERE shorturl = ?"
	args = [self.shorturl]
        self.log.info("incrementing count")

        self.do_update(q, args)
        self.count += 1

    def clear_url_title(self, shorturl):
	q = r"UPDATE url SET title = %s WHERE shorturl = %s"

	args = ['', shorturl]

        self.do_update(q, args)

    def set_url_desc(self, shorturl, desc):
	q = r"UPDATE url SET description = %s WHERE shorturl = %s"

	args = [desc, shorturl]

        self.do_update(q, args)

    def get_type(self):
	try:
	    type = None
	    info = self.browser.response().info()
	    if 'Content-type' in info:
		type = info['Content-type']

	    return type
	except Exception, e:
	    print str(e)

    def clear_title(self):
	h = find_url_helper(self.url)
	return h and h.clear_title

    def set_url_nsfw(self, nsfw):
	q = r"UPDATE url SET nsfw = ? WHERE shorturl = ?"

	args = [nsfw, self.shorturl]

        self.do_update(q, args)

    def set_url_type(self, shorturl, type):
	q = r"UPDATE url SET type = %s WHERE shorturl = %s"

	args = [type, shorturl]

        self.do_update(q, args)

    def add_url(self):
	args = [self.url, self.shorturl, self.nick, self.title, self.nsfw, self.channel]

	q  = r"INSERT INTO url (url, shorturl, nick, first_seen, "
        q += r"title, nsfw, channel"

	if self.type is not None:
	    q += r", type"
	    args.append(self.type)
	if self.description is not None:
	    q += r", description"
	    args.append(self.description)

	q += r") VALUES(?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?"
	#q += r") VALUES(%s, %s, NOW(), %s, %s, %s"
	if self.type is not None:
#	    q += r", %s"
	    q += r", ?"
	if self.description is not None:
#	    q += r", %s"
	    q += r", ?"

	q += r")"

        self.do_update(q, args)

    def open_url(self, url):
        r = self.browser.open(url)
        try:
            headers = r.info()
            if 'Content-Encoding' in headers:
                if headers['Content-Encoding'] == 'gzip':
                    gz = gzip.GzipFile(fileobj = r, mode = 'rb')
                    html = gz.read()
                    gz.close()
                    headers['Content-Type'] = 'text/html; charset=utf-8'
                    r.set_data(html)
                    self.browser.set_response(r)
        except Exception, e:
            print e.__class__.__name__
            print e

        return r

    def get_type(self):
        try:
            type = None
            info = self.browser.response().info()
            if 'Content-type' in info:
                type = info['Content-type']
            else:
                print "No Content-type"

            return type

        except Exception, e:
            print str(e)

    def clear_title(self, url):
        h = find_url_helper(url)
        return h and h.clear_title

    def get_description(self, url, resp):
        description = None

        type = self.get_type()

        h = find_url_helper(url)
        if h is not None:
            self.description = h.fetch(self, url, resp)
	    return
        if 'html' not in type:
            return None

        try:
            s = BeautifulSoup(resp.read())
            meta = s.findAll('meta')
            for tag in meta:
                desc = False
                for attr in tag.attrs:
                    if attr[0].lower() == 'property' and attr[1].lower() == 'og:description':
                        desc = True
                    if attr[0].lower() == 'name' and attr[1].lower() == 'description':
                        desc = True
                    if attr[0].lower() == 'content':
                        content = attr[1]
                    if desc:
                        description = content
        except Exception, e:
            print "EXCEPTION: %s" % str(e)

        self.description = description

    def fetch(self):
	url = self.url
        r = self.open_url(url)

        try:
            self.browser.cj.save('cookies.txt')
        except AttributeError, e:
            pass

        title = u""
        headers = r.info()
        if 'Content-type' in headers and 'text/html' in headers['Content-type']:
            try:
                s = BeautifulSoup(r.read())
                if s.title:
                    title = s.title.string
                    if title:
                       title = (" ".join(title.split())).strip()
            except urllib2.URLError, e:
                raise e
            except mechanize.BrowserStateError, e:
                title = u""
            except urllib2.HTTPError, e:
                print "Exception HTTPError " + str(e)
                title = u""
            except HTMLParser.HTMLParseError, e:
                title = u""

        type = self.get_type()
        self.get_description(url, r)

        if self.clear_title(url):
            title = None

        if title is None:
            title = u""

	self.title = title
	self.valid = True

    def timeAgo(self):
	ago = ""

	now_tm = datetime.datetime.utcnow()
	then_tm = self.first_seen

	seconds = now_tm.second - then_tm.second
	minutes = now_tm.minute - then_tm.minute
	hours   = now_tm.hour - then_tm.hour
	days    = now_tm.day - then_tm.day
	months  = now_tm.month  - then_tm.month
	years   = now_tm.year - then_tm.year

	# We want all positives, so lets make it go
	if seconds < 0:
	    seconds += 60
	    minutes -= 1

	if minutes < 0:
	    minutes += 60
	    hours -= 1

	if hours < 0:
	    hours += 24
	    days -= 1

	if days < 0:
	    if now_tm.month == 4 or now_tm.month == 6 or \
                now_tm.month == 9 or now_tm.month == 11:
		days += 30
	    elif now_tm.month == 2:
		if now_tm.year % 4 == 0 and  now_tm.year % 100 != 0:
		    days += 29
		else:
		    days += 28
	    else:
		days += 31
	    months -= 1

	if months < 0:
	    months += 12
	    years -= 1

	if years > 0:
	    hours = minutes = seconds = 0
	    ago = str(years) + "y"

	if months > 0:
	    hours = minutes = seconds = 0
	    if ago != "":
		ago += ", "
	    ago += str(months) + "m"

	if days > 0:
	    minutes = seconds = 0
	    if ago != "":
		ago += ", "
	    ago += str(days) + "d"

	if hours > 0:
	    seconds = 0
	    if ago != "":
		ago += ", "
	    ago += str(hours) + "h"

	if minutes > 0:
	    if ago != "":
		ago += ", "
	    ago += str(minutes) + "m"

	if seconds > 0:
	    if ago != "":
		ago += ", "
	    ago += str(seconds) + "s"
	else:
	    if ago == "":
		ago = "0s"
	    ago += " ago"

	return ago


if __name__ == "__main__":
    browser = SingletonBrowser.SingletonBrowser()
    filename = "test.sqlite"
    if os.path.exists(filename):
	db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_COLNAMES)
    else:
	db = sqlite3.connect(filename, detect_types=sqlite3.PARSE_COLNAMES)
	cursor = db.cursor()
	q = r"CREATE TABLE url ( url TEXT, shorturl TEXT, nick TEXT, first_seen TIMESTAMP DEFAULT (DATETIME('now')), title TEXT, nsfw INT, type TEXT, description TEXT, channel TEXT, count INT DEFAULT 1 )"
	cursor.execute(q)
	db.commit()

    info = SnarferInfo(db, browser, "relative", "#rit", "http://i.imgur.com/LWHmU.jpg", True)
    if not info.valid:
	info.fetch()
        info.shorturl = "http://ln-s.net/blah"
        info.add_url()
    print info

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
