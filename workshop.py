from multiprocessing                        import Value
from backend                                import Backend
from frontend                               import Labyrinth

class Main():

    def __init__(self, *args):

        shared_direction                = Value('i', 0)

        bkd = Backend()
        bkd.start_receiver(shared_direction, bkd.receiver_socket)
        lab = Labyrinth(shared_direction)

Main()


