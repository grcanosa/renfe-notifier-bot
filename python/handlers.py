"""


"""

from telegram import Updater 

import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

class ConvStates(Enum):
    OPTION = 1
    STATION = 2
    DATE = 3
    NUMERIC_OPTION = 4


def h_date(bot, update):
