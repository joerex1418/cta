import typing
import pathlib

class APIAuth(typing.NamedTuple):
    key:str
    
with pathlib.Path(__file__).parent().parent().joinpath("key.txt").open("r") as fp:
    key = fp.read().strip()

auth = APIAuth(key)