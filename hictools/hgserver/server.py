import itertools
from typing import List
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import UJSONResponse

from .utils import TileSetDB, TileSet


def create_app(db):
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        await db.connect()

    @app.on_event("shutdown")
    async def shutdown_event():
        await db.disconnect()

    # **************************************db dependant operation********************************#
    async def fetch_tilesets(**kwargs):
        tilesets = await db.query(**kwargs)
        uuids_remove = []
        for uuid in list(tilesets.keys()):
            if not Path(tilesets[uuid]['datafile']).exists():
                uuids_remove.append(uuid)
                del tilesets[uuid]
        await db.remove(uuids_remove)
        return tilesets
    # *******************************************************************************************#

    # handling ordered by through fetch_tilesets
    @app.get('/api/v1/tilesets/', response_class=UJSONResponse)
    async def list_tilesets(limit: int = Query(None),
                            datatype: List[str] = Query(None, alias="dt"),
                            filetype: List[str] = Query(None, alias="t")
                            ):
        tilesets = await fetch_tilesets(datatype=datatype, filetype=filetype)
        return {
            'count': len(tilesets),
            'next': None,
            'previous': None,
            'results': [TileSet.meta(tileset)
                        for tileset in tilesets.values()]
        }

    @app.get('/api/v1/chrom-sizes/', response_class=UJSONResponse)
    async def chromsizes():
        pass

    @app.get('/api/v1/tileset_info/', response_class=UJSONResponse)
    async def tileset_info(uuids: List[str] = Query(None, alias="d")):
        tilesets = await fetch_tilesets(uuid=uuids)
        info = {}
        existed_uuids = set(uuids) & set(tilesets.keys())

        for uuid in existed_uuids:
            info[uuid] = TileSet.tileset_info(tilesets[uuid])
        for uuid in set(uuids) - existed_uuids:
            info[uuid] = {'error': f"No such tileset with uuid: {uuid}"}

        return info

    @app.get('/api/v1/tiles/', response_class=UJSONResponse)
    async def tiles(uuids: List[str] = Query(..., alias="d")):
        uuid_tids = {uuid: list(tids)
                     for uuid, tids
                     in itertools.groupby(uuids, lambda x: x.split('.')[0])}
        tilesets = await fetch_tilesets(uuid=list(uuid_tids.keys()))
        tiles_list = [TileSet.tiles(tilesets[uuid], uuid_tids[uuid])
                      for uuid in tilesets]

        return {tid: tile
                for uuid_tiles in tiles_list
                for tid, tile in uuid_tiles}

    @app.post('/api/v1/tilesets/')
    async def append_tilesets():
        pass

    @app.post('/api/v1/chrom-sizes/')
    async def append_chrom_sizes():
        pass

    return app


class Server(object):
    def __init__(self, tileset_db=TileSetDB()):
        self.db = tileset_db
        self.app = create_app(self.db)

    def run(self, store_uri=None, **kwargs):
        if store_uri is not None:
            self.db.store_uri = store_uri
        uvicorn.run(self.app, **kwargs)