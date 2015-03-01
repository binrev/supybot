###
# Copyright (c) 2005, Jeremiah Fincher
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

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('Snarfer', True)
    if yn("""This plugin offers a snarfer that will go retrieve a shorter
             version of long URLs that are sent to the channel.  Would you
             like this snarfer to be enabled?""", default=False):
        conf.supybot.plugins.Snarfer.shrinkSnarfer.setValue(True)

class ShrinkService(registry.OnlySomeStrings):
    validStrings = ('ln', 'tiny', 'dnb', 'none')

Snarfer = conf.registerPlugin('Snarfer')
conf.registerChannelValue(Snarfer, 'shrinkSnarfer',
    registry.Boolean(True, """Determines whether the
    shrink snarfer is enabled.  This snarfer will watch for URLs in the
    channel."""))
conf.registerChannelValue(Snarfer.shrinkSnarfer, 'showDomain',
    registry.Boolean(False, """Determines whether the snarfer will show the
    domain of the URL being snarfed along with the shrunken URL."""))
conf.registerChannelValue(Snarfer, 'nonSnarfingRegexp',
    registry.Regexp(None, """Determines what URLs are to be snarfed; URLs
    matching the regexp given will not be snarfed.  Give the empty string if
    you have no URLs that you'd like to exclude from being snarfed."""))
conf.registerChannelValue(Snarfer, 'outFilter',
    registry.Boolean(False, """Determines whether the bot will shrink the URLs
    of outgoing messages if those URLs are longer than
    supybot.plugins.Snarfer.minimumLength."""))
conf.registerChannelValue(Snarfer, 'extendedInfo',
    registry.Boolean(True, """Determines whether extended info is provided to
    the channel after a URL is processed."""))

conf.registerChannelValue(Snarfer, 'linkcache_config',
    registry.String("", """Location of the linkcache config file"""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
