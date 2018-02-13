import appdaemon.appdaemon
import appdaemon.admain as admain
import appdaemon.conf as conf
import appdaemon.utils as utils

import asyncio
import math


_main_loop_blocker = asyncio.Event()


def unblock():
    def _unblock():
        global _main_loop_blocker
        utils.log(conf.logger, "INFO", "_Unblock")
        _main_loop_blocker.set()

    utils.log(conf.logger, "INFO", "Unblock")
    conf.loop.call_soon_threadsafe(_unblock())


def block():
    def _block():
        global _main_loop_blocker
        utils.log(conf.logger, "INFO", "_Block")
        _main_loop_blocker.clear()

    utils.log(conf.logger, "INFO", "Block")
    conf.loop.call_soon_threadsafe(_block())


@asyncio.coroutine
def _do_every(period, f):
    global _main_loop_blocker
    t = math.floor(utils.get_now_ts())
    while not conf.stopping:
        yield from _main_loop_blocker.wait()
        utils.log(conf.logger, "INFO", "Loop")
        t += conf.interval
        yield from f(t)


def main():
    appdaemon.appdaemon.do_every = _do_every
    admain.main()


if __name__ == '__main__':
    main()
