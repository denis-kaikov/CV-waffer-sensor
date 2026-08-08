from enum import IntEnum


class SystemState(IntEnum):
    INITIALIZING = 0
    READY = 1
    CAPTURING = 2
    PROCESSING = 3
    RESULT_READY = 4
    ERROR = 5
    MAINTENANCE = 6
