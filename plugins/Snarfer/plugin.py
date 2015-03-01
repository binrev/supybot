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

import ConfigParser
import linkcache.linkcache

class Snarfer(callbacks.PluginRegexp):
    regexps = ['shrinkSnarfer']
    def __init__(self, irc):
        self.__parent = super(Snarfer, self)
        self.__parent.__init__(irc)

        config_file = self.registryValue('linkcache_config')
        config = ConfigParser.ConfigParser()
        cfile = open(config_file, "r")
        config.readfp(cfile)
        self.cache = linkcache.linkcache.LinkCache(config)
        print "Snarfer initialized."

    def reload(self):
        reload(info)

    def die(self):
        pass

    def callCommand(self, command, irc, msg, *args, **kwargs):
        try:
            self.__parent.callCommand(command, irc, msg, *args, **kwargs)
        except utils.web.Error, e:
            irc.error(str(e))

    def shrinkSnarfer(self, irc, msg, match):
        r".*"
#        r"(^|\s+)(([\|\$\!\~\^]+)|)(((([\w\-]+\.)+)([\w\-]+))(((/[\w\-\.%\(\)~]*)+)+|\s+|[\!\?\.,;]+|$)|https?://[^\]>\s]*)"
        channel = msg.args[0]
        nick = msg.nick

        if not irc.isChannel(channel):
            self.log.info("wrong channel")
            return
        if self.registryValue('shrinkSnarfer', channel):
            try:
                result = self.cache.parse_line(match.group(0), nick, True, channel)
                if not result:
                    return
            except Exception, e:
                m = irc.reply(str(e), prefixNick=False)
                m.tag('shrunken')
                return

            print result

            elapsed = result.last_seen - result.first_seen

            if result.last_seen != result.first_seen and \
               elapsed.total_seconds() < 10*60:
                return

            shorturl = result.shorturl

            ext_info = self.registryValue('extendedInfo', channel)
            if not ext_info and shorturl is not None:
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
            elif shorturl:
                m = irc.reply(shorturl, prefixNick=False)
                m.tag('shrunken')
                description = unicode(result)
                if description:
                    m = irc.reply(description, prefixNick=False)
                    m.tag('shrunken')

    shrinkSnarfer = urlSnarfer(shrinkSnarfer)
Class = Snarfer
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
