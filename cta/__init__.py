"""


Station IDs
-----------
0-29999     = Bus stops
30000-39999 = Train stops
40000-49999 = Train stations (parent stops)

"""

from .bus import Stop
from .bus import Route

from .train import follow
from .train import get_arrivals