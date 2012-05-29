import asyncore, errno, os, re, sqlite3, subprocess, sys, time, urllib2
from .. import FruitConfigParser

class Cache(object):
    def __init__(self, directory):
        self.__directory = directory
        self.__base_url = ""
        self.__compression = {}
        self.__conn = sqlite3.connect(directory + os.path.sep + "cache.sqlite")
        self.__conn.execute("""
create table if not exists cache
(url text, etag text, downloaded integer, max_age integer, last_used integer, size integer)""")

        self.__conn.execute("""create index if not exists cache_url on cache(url)""")
        self.__conn.execute("""create index if not exists cache_last_used on cache(last_used)""")

    def __handle_server_connection(self):
        self.__server_connection.send_keepalive()
        asyncore.loop(timeout=0, use_poll=True, count=1)

    @staticmethod
    def __printable_url(url):
        if len(url) > 40: url = re.sub(r"^https?://", "", url)
        if len(url) > 40: url = url[:16] + "..." + url[-21:]
        return url

    def __url_to_filename(self, url):
        url = re.sub(r"^https?://", "", url)
        if re.search(r"[^A-Za-z0-9_/.-]", url) or os.path.sep * 2 in url or ".." in url:
            print("client: can't download '%s' which contains an illegal character." % url)
            sys.exit(1)

        return self.__directory + os.path.sep + url

    def __download(self, url, etag=None):
        leaf_url = url
        if leaf_url.startswith(self.__base_url): leaf_url = leaf_url[len(self.__base_url):]
        if leaf_url.startswith("/"): leaf_url = leaf_url[1:]
        compression = self.__compression[leaf_url] if leaf_url in self.__compression else "none"
        if compression == "xz":
            suffix = ".xz"
            command = "unxz"
        else:
            suffix = ""
            command = None

        request = urllib2.Request(url + suffix)
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
            if not os.path.exists(os.path.dirname(filename)): os.makedirs(os.path.dirname(filename))

            try:
                os.unlink(filename)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise

            with open(filename + suffix, "wb") as out:
                so_far = 0
                while True:
                    self.__handle_server_connection()
                    data = inp.read(4096)
                    so_far += len(data)
                    percent = "%d%%" % (so_far * 100 / length) if length is not None else str(so_far)
                    sys.stdout.write("Downloading   %s [%s]...\r" % (self.__printable_url(url), percent))
                    out.write(data)
                    if len(data) == 0: break

                print

            if command is not None:
                sys.stdout.write("Uncompressing %s...  " % self.__printable_url(url))
                sys.stdout.flush()
                subprocess.call([command, filename + suffix])
                print("done.")

            self.__conn.execute("delete from cache where url = ?", (url,))
            self.__conn.execute("insert into cache values (?, ?, ?, ?, ?, ?)",
                                (url, new_etag, self.__start, max_age, self.__start, os.stat(filename).st_size))
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

    def __load(self, url):
        self.__handle_server_connection()
        self.__start = time.time()
        row = self.__conn.execute("select etag, downloaded, max_age from cache where url = ?", (url,)).fetchone()
        if row is None:
            print "URL %s : not cached." % self.__printable_url(url)
            self.__download(url)
        elif row[1] + row[2] > self.__start:
            print "URL %s : cached and up to date." % self.__printable_url(url)
            self.__conn.execute("update cache set last_used = ? where url = ?", (self.__start, url))
        else:
            sys.stdout.write("URL %s : checking cache...  " % self.__printable_url(url))
            sys.stdout.flush()
            self.__download(url, row[0])

        return self.__url_to_filename(url)

    def load_scene(self, server_connection, url):
        self.__server_connection = server_connection
        self.__base_url = url

    def run(self):
        cfg = self.__load(self.__base_url + "scene.cfg")
        scene = FruitConfigParser()
        scene.read(cfg)

        self.__compression = dict(scene.items("compression"))

        for thing in scene.get("scene", "things").split(" "):
            egg = scene.get(thing, "egg")
            self.__load(self.__base_url + egg)

        for texture in scene.get_all("textures", "texture"):
            self.__load(self.__base_url + texture)

        self.__conn.commit()
        self.__server_connection.scene_loaded()
