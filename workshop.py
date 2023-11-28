from multiprocessing                        import Pipe
from backend                                import Backend
from frontend                               import Labyrinth

class Main():

    def __init__(self, *args):

        self.recv_conn, self.send_conn = Pipe(duplex = False)

        bkd = Backend()
        bkd.start_receiver(self.send_conn, bkd.receiver_socket)
        lab = Labyrinth(self.recv_conn)

Main()


