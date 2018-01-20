from subprocess import Popen, DEVNULL, TimeoutExpired


def run_process(*args):
    return Popen(args, stdout=DEVNULL, stderr=DEVNULL)


def terminate_process(process):
    process.terminate()


def wait_for_process(process, timeout=10):
    try:
        process.wait(timeout)
    except TimeoutExpired:
        process.kill()
        process.wait()


def is_process_running(process):
    return process.poll() is None
