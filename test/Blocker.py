import appdaemon.conf as conf
import appdaemon.utils as utils

import asyncio


_main_loop_blocker = asyncio.Event()


def unblock():
    @asyncio.coroutine
    def _unblock():
        global _main_loop_blocker
        utils.log(
            conf.logger, "INFO", "Unblock")
        _main_loop_blocker.set()

    asyncio.run_coroutine_threadsafe(_unblock(), conf.loop)


def block():
    @asyncio.coroutine
    def _block():
        global _main_loop_blocker
        utils.log(conf.logger, "INFO", "Block")
        _main_loop_blocker.clear()

    asyncio.run_coroutine_threadsafe(_block(), conf.loop)


@asyncio.coroutine
def wait():
    yield from _main_loop_blocker.wait()


def is_blocked():
    return not _main_loop_blocker.is_set()
