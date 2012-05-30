import argparse, asyncore, os, socket, sys, time

from . import gameloop
from .cache import Cache
from .. import messaging
from ..rpc import account_pb2, game_pb2

args = None

class ServerConnection(messaging.Rpc):
    """This class connects to the server, and handles messages that
    arrive.  The superclass provides a function to send messages back
    to the server (send_rpc).  These messages are sent asynchronously,
    when asyncore.loop is entered.

    The superclass also catches and displays exceptions.  It then
    invokes uncaught_exception; the client exits when this function is
    called, but the server does nothing because it should attempt to
    carry on running."""

    def __init__(self, sock, cache):
        messaging.Rpc.__init__(self, sock=sock)
        self.__cache = cache
        self.__last_keepalive_received = time.time()
        self.__last_keepalive_sent = 0
        self.app = None

    def handle_close(self):
        print "Connection to server was lost."
        sys.exit(3)

    def send_keepalive(self):
        if self.__last_keepalive_sent + messaging.KEEPALIVE_FREQUENCY < time.time():
            data = account_pb2.KeepAlive()
            self.send_rpc(data)
            self.__last_keepalive_sent = time.time()

    def keepalive(self, task):
        self.send_keepalive()

        if self.__last_keepalive_received < time.time() - messaging.KEEPALIVE_PERMITTED_DELAY:
            self.handle_close()

        return task.again

    def scene_loaded(self):
        data = game_pb2.SceneLoaded()
        self.send_rpc(data)
        self.app = None

    def uncaught_exception(self, e):
        sys.exit(1)

    def message_received(self, name, msg):
        if name == "account_pb2.Kick":
            sys.exit(0)
        elif name == "account_pb2.TellUser":
            data = account_pb2.TellUser()
            data.ParseFromString(msg)
            print data.message
        elif name == "account_pb2.Error":
            data = account_pb2.Error()
            data.ParseFromString(msg)
            print data.message
        elif name == "account_pb2.KeepAlive":
            self.__last_keepalive_received = time.time()
        elif name == "game_pb2.LoadScene":
            data = game_pb2.LoadScene()
            data.ParseFromString(msg)
            self.__scene = self.__cache.load_scene(self, data.sc_url)
            self.app = self.__cache
        elif name == "game_pb2.Start":
            data = game_pb2.Start()
            data.ParseFromString(msg)
            self.__start_game(data.player_tag)
        elif name == "game_pb2.AddObject":
            data = game_pb2.AddObject()
            data.ParseFromString(msg)
            self.app.server_created_object(data.tag, data.height, data.radius)
        elif name == "game_pb2.RemoveObject":
            data = game_pb2.RemoveObject()
            data.ParseFromString(msg)
            self.app.server_removed_object(data.tag)
        elif name == "game_pb2.ThingState":
            data = game_pb2.ThingState()
            data.ParseFromString(msg)
            self.app.server_moves_thing(data.tag, data.location.x, data.location.y, data.location.z,
                                        data.velocity.x, data.velocity.y, data.velocity.z,
                                        data.angle, data.angular_velocity)

        elif name == "game_pb2.EventListen":
            data = game_pb2.EventListen()
            data.ParseFromString(msg)
            self.app.accept(data.event, self.__send_event_to_server, [data.tag])

    def __send_event_to_server(self, tag, *args):
        data = game_pb2.EventOccurred()
        data.tag = tag
        data.args.extend([self.encode_variant(arg) for arg in args])
        self.send_rpc(data)

    def __start_game(self, player_tag):
        self.app = gameloop.FriendlyFruit(self, player_tag)
        self.app.create_scene(self.__scene)
        self.app.doMethodLater(messaging.KEEPALIVE_FREQUENCY, self.keepalive, "KeepAliveTask")

def parse_command_line():
    global args

    argparser = argparse.ArgumentParser(description="Client for the FriendlyFruit game network.")

    argparser.add_argument("-u", "--user-id", required=True,
                           help="connect using this account", dest="user_id")

    argparser.add_argument("-p", "--password", required=True,
                           help="your password", dest="password")

    argparser.add_argument("--port", default=41810, type=int,
                           help="connect to the server on this port", dest="port")

    argparser.add_argument("--register", action="store_true",
                           help="register a new account on the server", dest="new_account")

    argparser.add_argument("host", help="connect to this machine")

    args = argparser.parse_args()

def run(toplevel_dir):
    parse_command_line()

    sock = socket.create_connection((args.host, args.port))
    cache_dir = toplevel_dir + os.path.sep + "cache"
    if not os.path.exists(cache_dir): os.mkdir(cache_dir)
    server_connection = ServerConnection(sock, Cache(cache_dir))

    if args.new_account:
        register = account_pb2.NewAccount()
        register.user_id = args.user_id
        register.password = args.password
        server_connection.send_rpc(register)
    else:
        login = account_pb2.Login()
        login.user_id = args.user_id
        login.password = args.password
        server_connection.send_rpc(login)

    while True:
        asyncore.loop(use_poll=True, count=1)
        if server_connection.app is not None:
            server_connection.app.run()
