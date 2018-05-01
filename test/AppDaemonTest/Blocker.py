import appdaemon.utils as utils

import asyncio


daemon = None


class Blocker:
    def __init__(self, name):
        self.name = name
        self.__blocker = asyncio.Event()

    def unblock(self):
        @asyncio.coroutine
        def _unblock():
            utils.log(
                daemon.logger, "INFO", "Unblock", self.name)
            self.__blocker.set()

        asyncio.run_coroutine_threadsafe(_unblock(), daemon.loop)

    def block(self):
        @asyncio.coroutine
        def _block():
            global _main_loop_blocker
            utils.log(daemon.logger, "INFO", "Block", self.name)
            self.__blocker.clear()

        asyncio.run_coroutine_threadsafe(_block(), daemon.loop)

    @asyncio.coroutine
    def wait(self):
        yield from self.__blocker.wait()

    def is_blocked(self):
        return not self.__blocker.is_set()


main_blocker = Blocker('main_blocker')
set_state_blocker = Blocker('set_state_blocker')
