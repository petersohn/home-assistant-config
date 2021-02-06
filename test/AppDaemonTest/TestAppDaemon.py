import appdaemon.appdaemon
import appdaemon.scheduler
import appdaemon.__main__ as admain

import Blocker

import concurrent
import math
import datetime
import sys


queue_joiner = concurrent.futures.ThreadPoolExecutor(max_workers=1)
_old_scheduler_sleep = None
_old_appdaemon_init = None


async def _kick(self):
    pass

async def _sleep(self, delay):
    global _old_scheduler_sleep
    while Blocker.main_blocker.is_blocked() or \
            Blocker.main_blocker.is_blocked():
        await Blocker.main_blocker.wait()
        await Blocker.set_state_blocker.wait()
    return await _old_scheduler_sleep(self, delay)


def _appdaemon_init(self, *args, **kwargs):
    _old_appdaemon_init(self, *args, **kwargs)
    Blocker.main_blocker = Blocker.Blocker('main_blocker', self)
    Blocker.set_state_blocker = Blocker.Blocker('set_state_blocker', self)
    Blocker.daemon = self
    Blocker.main_blocker.block()
    Blocker.set_state_blocker.unblock()

def main():
    global _old_scheduler_sleep
    global _old_appdaemon_init

    appdaemon.scheduler.Scheduler.kick = _kick
    _old_scheduler_sleep = appdaemon.scheduler.Scheduler.sleep
    appdaemon.scheduler.Scheduler.sleep = _sleep
    _old_appdaemon_init = appdaemon.appdaemon.AppDaemon.__init__
    appdaemon.appdaemon.AppDaemon.__init__ = _appdaemon_init
    admain.main()


if __name__ == '__main__':
    main()
