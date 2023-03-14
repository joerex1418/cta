import asyncio

import httpx

from .auth import auth


async def _fetch_one(session:httpx.AsyncClient,url:str):
    params = {"key": auth.bus, "format": "json"}
    
    r = await session.get(url,params=params)
    
    return r

async def _fetch_all(_itemlist:list):
    async with httpx.AsyncClient() as session:
        if isinstance(_itemlist[0],str):
            tasks = (asyncio.create_task(_fetch_one(session,url)) for url in _itemlist)
        
        responses =  await asyncio.gather(*tasks)
        
        return responses

def fetch_all(_itemlist:list):
    if not isinstance(_itemlist,list):
        _itemlist = [_itemlist]
    return asyncio.run(_fetch_all(_itemlist))



