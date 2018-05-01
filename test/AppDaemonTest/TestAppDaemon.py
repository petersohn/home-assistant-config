import appdaemon.appdaemon
import appdaemon.admain as admain

import Blocker

import concurrent
import math
import datetime


queue_joiner = concurrent.futures.ThreadPoolExecutor(max_workers=1)


async def _do_every(self, period, f):
    Blocker.main_blocker.block()
    Blocker.set_state_blocker.unblock()

    self.now = datetime.datetime.strptime(
        self.starttime, "%Y-%m-%d %H:%M:%S").timestamp()
    t = math.floor(self.now)
    while not self.stopping:
        await Blocker.main_blocker.wait()
        await Blocker.set_state_blocker.wait()
        await self.loop.run_in_executor(queue_joiner, self.q.join)

        if (Blocker.main_blocker.is_blocked()
                or Blocker.set_state_blocker.is_blocked()):
            continue

        t += self.interval
        await f(t)


_old_appdaemon_init = None


def _appdaemon_init(self, *args, **kwargs):
    Blocker.daemon = self
    _old_appdaemon_init(self, *args, **kwargs)


def main():
    appdaemon.appdaemon.AppDaemon.do_every = _do_every
    global _old_appdaemon_init
    _old_appdaemon_init = appdaemon.appdaemon.AppDaemon.__init__
    appdaemon.appdaemon.AppDaemon.__init__ = _appdaemon_init
    admain.main()


if __name__ == '__main__':
    main()
