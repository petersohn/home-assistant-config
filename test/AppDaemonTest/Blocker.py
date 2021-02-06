import asyncio


daemon = None


class Blocker:
    def __init__(self, name, ad):
        self.name = name
        self.logger = ad.logging.get_child(name)
        self.__blocker = asyncio.Event()

    def unblock(self):
        async def _unblock():
            self.logger.info("Unblock")
            self.__blocker.set()

        asyncio.run_coroutine_threadsafe(_unblock(), daemon.loop)

    def block(self):
        async def _block():
            global _main_loop_blocker
            self.logger.info("Block")
            self.__blocker.clear()

        asyncio.run_coroutine_threadsafe(_block(), daemon.loop)

    async def wait(self):
        await self.__blocker.wait()

    def is_blocked(self):
        return not self.__blocker.is_set()


main_blocker = None
set_state_blocker = None
