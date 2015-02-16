#Copyright 2015 - Sean Donovan
# For evaluation we need serial numbers. This makes that happen. 

from threading import Lock
class serial_logging(object):

    INSTANCE = None

    def __init__(self):
        self.number = 0
        self.lock = Lock()

    @classmethod
    def get_number(cls):
        if cls.INSTANCE is None:
            cls.INSTANCE = serial_logging()

        with cls.INSTANCE.lock:
            current = cls.INSTANCE.number
            cls.INSTANCE.number = cls.INSTANCE.number + 1
        return current

