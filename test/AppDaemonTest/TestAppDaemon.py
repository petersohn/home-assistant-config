import appdaemon.appdaemon
import appdaemon.admain as admain
import appdaemon.conf as conf
import appdaemon.utils as utils

import Blocker

import asyncio
import concurrent
import math


queue_joiner = concurrent.futures.ThreadPoolExecutor(max_workers=1)


@asyncio.coroutine
def _do_every(period, f):
    Blocker.main_blocker.block()
    Blocker.set_state_blocker.unblock()

    t = math.floor(utils.get_now_ts())
    while not conf.stopping:
        yield from Blocker.main_blocker.wait()
        yield from Blocker.set_state_blocker.wait()
        yield from conf.loop.run_in_executor(
            queue_joiner, appdaemon.appdaemon.q.join)

        if (Blocker.main_blocker.is_blocked()
                or Blocker.set_state_blocker.is_blocked()):
            continue

        t += conf.interval
        yield from f(t)


def main():
    appdaemon.appdaemon.do_every = _do_every
    admain.main()


if __name__ == '__main__':
    main()
