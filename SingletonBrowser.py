#!/usr/bin/env python
import mechanize
import socket

# This is a singleton browser implementation

class SingletonBrowser:
    __instance = None

    def __init__(self, cookiejar=None, passwords=None):
        if SingletonBrowser.__instance is None:
            __instance = SingletonBrowser.__impl(cookiejar, passwords)
            SingletonBrowser.__instance = __instance
            self.__dict__['_SingletonBrowser__instance'] = __instance

    def __getattr__(self, attr):
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        return setattr(self.__instance, attr, value)
    class __impl(mechanize.Browser):
        def __init__(self, cookiejar, passwords):
            mechanize.Browser.__init__(self)
            cj = None
            if cookiejar:
                cj = mechanize.MozillaCookieJar()
                cj.load(cookiejar)
                self.set_cookiejar(cj)

            self.cj = cj

            socket.setdefaulttimeout(10)

            if passwords:
                for url in passwords:
                    self.add_password(url, passwords[url][0], passwords[url][1])
            self.set_handle_robots(False)
            self.set_handle_refresh(False)
            self.addheaders = [
                ('User-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2')
            ]
#            self.set_debug_http(True)

if __name__ == '__main__':
    b = SingletonBrowser('cookies.txt')

    f = b.open("http://www.google.com")

    print f.read()

# vim: ts=4 sw=4 et
