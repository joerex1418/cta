import json
import random
import pathlib


class APIAuth:
    __slots__ = ("_data",)
    def __init__(self):
        with pathlib.Path(__file__).parent.parent.joinpath("key.json").open("r") as fp:
            self._data = json.load(fp)
        
    @property
    def bus(self):
        _bus = self._data["bus"]
        return _bus[random.randrange(0,len(_bus))]

    @property
    def train(self):
        _train = self._data["train"]
        return _train[random.randrange(0,len(_train))]
    
auth = APIAuth()


