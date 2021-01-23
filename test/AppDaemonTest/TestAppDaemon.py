import appdaemon.appdaemon
import appdaemon.scheduler
import appdaemon.__main__ as admain

import Blocker

import concurrent
import math
import datetime


queue_joiner = concurrent.futures.ThreadPoolExecutor(max_workers=1)


async def _kick(self):
    pass

async def _sleep(self, delay):
    while Blocker.main_blocker.is_blocked() or \
            Blocker.main_blocker.is_blocked():
        await Blocker.main_blocker.wait()
        await Blocker.set_state_blocker.wait()
    return False


_old_appdaemon_init = None


def _appdaemon_init(self, *args, **kwargs):
    Blocker.daemon = self
    _old_appdaemon_init(self, *args, **kwargs)
    Blocker.main_blocker.block()
    Blocker.set_state_blocker.unblock()

def main():
    appdaemon.scheduler.Scheduler.kick = _kick
    appdaemon.scheduler.Scheduler.sleep = _sleep
    global _old_appdaemon_init
    _old_appdaemon_init = appdaemon.appdaemon.AppDaemon.__init__
    appdaemon.appdaemon.AppDaemon.__init__ = _appdaemon_init
    admain.main()


if __name__ == '__main__':
    main()
