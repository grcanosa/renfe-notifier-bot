"""

"""



class ConvStates(Enum):
    OPTION = 1
    STATION = 2
    DATE = 3
    NUMERIC_OPTION = 4


class RenfeBotConversations:
    class Conversation:
        def __init__(self, userid):
            self._userid = userid
            self.reset()

        def reset(self):
            self._option = 0
            self._origin = None
            self._dest = None
            self._date = None
            self._data = None      

    def __init__(self):
        self._conversations = {}

