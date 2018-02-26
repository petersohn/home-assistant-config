import appdaemon.conf as conf
import appdaemon.utils as utils

import asyncio


class Blocker:
    def __init__(self, name):
        self.name = name
        self.__blocker = asyncio.Event()

    def unblock(self):
        @asyncio.coroutine
        def _unblock():
            utils.log(
                conf.logger, "INFO", "Unblock", self.name)
            self.__blocker.set()

        asyncio.run_coroutine_threadsafe(_unblock(), conf.loop)

    def block(self):
        @asyncio.coroutine
        def _block():
            global _main_loop_blocker
            utils.log(conf.logger, "INFO", "Block", self.name)
            self.__blocker.clear()

        asyncio.run_coroutine_threadsafe(_block(), conf.loop)

    @asyncio.coroutine
    def wait(self):
        yield from self.__blocker.wait()

    def is_blocked(self):
        return not self.__blocker.is_set()


main_blocker = Blocker('main_blocker')
set_state_blocker = Blocker('set_state_blocker')
