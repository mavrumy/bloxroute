from lib.logging.proxy import LoggerProxy
from lib.logging.logger import Logger
from lib.message.client import ClientMessage
from lib.message.handler import MessageHandler
import socket
import select
import argparse
import multiprocessing
from multiprocessing.reduction import ForkingPickler
import pickle
import os.path as opath
from datetime import datetime, timedelta
from StringIO import StringIO
import struct

from lib.message.type import MessageType

MAX_CONNECTIONS = 5
POLL_INTERVAL = 1
POOL_SIZE = max(multiprocessing.cpu_count() - 2, 1)
BUFFER_SIZE = 1024
LOG_FOLDER = opath.join(opath.dirname(__file__), "../logs")
DEFAULT_HOST = "localhost"


def receive(pickled_connection, server_queue, stop_var, debug_var, log_queue, fileno):
    logger = LoggerProxy(log_queue, debug_var)
    connection = pickle.loads(pickled_connection)
    try:
        data = connection.recv(BUFFER_SIZE)
        if not data:
            logger.debug("client {} disconnected".format(connection.getsockname()))
            return fileno, False
        while data:
            msg = parse(data)
            if msg:
                handler = MessageHandler(msg, server_queue, connection, debug_var, stop_var, logger)
                handler.handle()
                data = data[msg.message_size:]
            con_events, _, _ = select.select([connection], [], [], 0)
            if len(con_events) > 0:
                data += connection.recv(BUFFER_SIZE)
            elif msg is None:
                logger.debug("invalid message received from client {}".format(connection.getsockname()))
                data = ""
        return fileno, True
    except socket.error as e:
        logger.debug("failed to receive data from {}, {}".format(connection.getsockname(), e))
        return fileno, False


def parse(buf):
        buf_size = len(buf)
        if buf_size < ClientMessage.HEADER_SIZE:
            return None
        msg_type_value, msg_data_size = struct.unpack("II", buf[:ClientMessage.HEADER_SIZE])
        if msg_data_size:
            if buf_size < ClientMessage.HEADER_SIZE + msg_data_size:
                return None
            msg_data = struct.unpack("{}s".format(msg_data_size),
                                     buf[ClientMessage.HEADER_SIZE: ClientMessage.HEADER_SIZE + msg_data_size])[0]
        else:
            msg_data = ""
        return ClientMessage(MessageType(msg_type_value), msg_data)


def handle_logging(log_queue, debug_var, last_process_time):
    if debug_var.value and not log_queue.empty() and \
            (datetime.now() - last_process_time > timedelta(minutes=1) or log_queue.qsize() > 10):
        logger = Logger(log_queue, LOG_FOLDER, debug_var)
        logger.handle()
        return datetime.now()
    else:
        return last_process_time


def main(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(0)
    try:
        server_socket.bind((host, port))
    except socket.error as e:
        print("fatal error - failed to bind server socket, {}".format(e))
        return
    server_socket.listen(MAX_CONNECTIONS)
    connections = {server_socket.fileno(): server_socket}
    manager = multiprocessing.Manager()
    pool = multiprocessing.Pool(POOL_SIZE)
    stop_var = manager.Value("i", 0)
    debug_var = manager.Value("i", 0)
    server_queue = manager.Queue()
    log_queue = manager.Queue()

    try:
        server_loop(connections, server_socket, pool, log_queue, server_queue, stop_var, debug_var)
    finally:
        for fileno in connections:
            connection = connections[fileno]
            connection.close()
        pool.close()


def server_loop(connections, server_socket, pool, log_queue, server_queue, stop_var, debug_var):
    stop_server = False
    logger_result = pool.apply_async(handle_logging, args=(log_queue, debug_var, datetime.now()))
    client_results = []
    idle_connections = connections.copy()
    active_connections = {}
    while not stop_server:
        try:
            socket_events, _, _ = select.select(idle_connections.values(), [], [], POLL_INTERVAL)
        except socket.error as e:
            print("select error {}, idle_connections - {}".format(e, idle_connections))
            socket_events = {}
        for socket_event in socket_events:
            if socket_event is server_socket:
                connection, client_address = server_socket.accept()
                print("client {} is now connected to server".format(client_address))
                connections[connection.fileno()] = connection
                idle_connections[connection.fileno()] = connection
            else:
                buf = StringIO()
                ForkingPickler(buf).dump(socket_event)
                pickled_connection = buf.getvalue()
                active_connections[socket_event.fileno()] = idle_connections.pop(socket_event.fileno())
                client_results.append(pool.apply_async(receive, args=(pickled_connection, server_queue, stop_var,
                                                                      debug_var, log_queue, socket_event.fileno())))
        if logger_result.ready():
            last_process_time = logger_result.get()
            logger_result = pool.apply_async(handle_logging, args=(log_queue, debug_var, last_process_time))
        pending_results = []
        for client_result in client_results:
            if client_result.ready():
                fileno, success = client_result.get()
                if success:
                    idle_connections[fileno] = active_connections.pop(fileno)
                else:
                    conn = connections.pop(fileno)
                    active_connections.pop(fileno, None)
                    conn.close()
            else:
                pending_results.append(client_result)
        client_results = pending_results
        stop_server = bool(stop_var.value)
    print("stopping server")
    for client_result in client_results:
        client_result.wait()
    logger_result.wait()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(prog="TCP server app")
    arg_parser.add_argument("-p", type=int, help="the server port (required)")
    arg_parser.add_argument("--host", type=str, default=DEFAULT_HOST,
                            help="the server host (default is {})".format(DEFAULT_HOST))
    args = arg_parser.parse_args()
    main(args.host, args.p)
