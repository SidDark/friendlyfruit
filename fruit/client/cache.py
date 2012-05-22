import os, re, sqlite3, sys, time, urllib, urllib2

class Cache(object):
    def __init__(self, directory):
        self.__directory = directory
        self.__conn = sqlite3.connect(directory + os.path.sep + "cache.sqlite")
        self.__conn.execute("""
create table if not exists cache
(url text, etag text, downloaded integer, max_age integer, last_used integer, size integer)""")

        self.__conn.execute("""create index if not exists cache_url on cache(url)""")
        self.__conn.execute("""create index if not exists cache_last_used on cache(last_used)""")

    @staticmethod
    def __printable_url(url):
        if len(url) > 40: url = re.sub(r"^https?://", "", url)
        if len(url) > 40: url = url[:16] + "..." + url[-21:]
        return url

    def __url_to_filename(self, url):
        url = re.sub(r"^https?://", "", url)
        return self.__directory + os.path.sep + urllib.quote_plus(url)

    def __download(self, url, etag=None):
        request = urllib2.Request(url)
        if etag is not None and etag != "": request.add_header("If-None-Match", etag)

        inp = None
        try:
            inp = urllib2.urlopen(request)
            if etag is not None: print "out of date."
            info = inp.info()
            length = int(info.getheader("Content-Length"))
            max_age = info.getheader("Cache-Control", "max-age=0")
            max_age = re.match(r".*max-age=(\d+)", max_age)
            max_age = int(max_age.group(1)) if max_age is not None else 0
            new_etag = info.getheader("ETag", "")
            filename = self.__url_to_filename(url)
            with open(filename, "wb") as out:
                so_far = 0
                while True:
                    data = inp.read(4096)
                    so_far += len(data)
                    percent = "%d%%" % (so_far * 100 / length) if length is not None else str(so_far)
                    sys.stdout.write("Downloading %s [%s]...\r" % (self.__printable_url(url), percent))
                    out.write(data)
                    if len(data) == 0: break

                print
                self.__conn.execute("delete from cache where url = ?", (url,))
                self.__conn.execute("insert into cache values (?, ?, ?, ?, ?, ?)",
                                    (url, new_etag, self.__start, max_age, self.__start, so_far))
                self.__conn.commit()
        except urllib2.HTTPError, e:
            if e.code == 304:
                print "cached."
                self.__conn.execute("update cache set downloaded = ?, last_used = ? where url = ?",
                                    (self.__start, self.__start, url))

                self.__conn.commit()
            else:
                print e
                sys.exit(1)
        finally:
            if inp is not None: inp.close()

    def load(self, url):
        self.__start = time.time()
        row = self.__conn.execute("select etag, downloaded, max_age from cache where url = ?", (url,)).fetchone()
        self.__conn.commit()
        if row is None:
            print "URL %s : not cached." % self.__printable_url(url)
            self.__download(url)
        elif row[1] + row[2] > self.__start:
            print "URL %s : cached and up to date." % self.__printable_url(url)
            self.__conn.execute("update cache set last_used = ? where url = ?", (self.__start, url))
            self.__conn.commit()
        else:
            sys.stdout.write("URL %s : checking cache...  " % self.__printable_url(url))
            sys.stdout.flush()
            self.__download(url, row[0])

        return self.__url_to_filename(url)
