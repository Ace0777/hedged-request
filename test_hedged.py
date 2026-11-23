import asyncio
import time

from hedged import hedged


def fake(*steps):
    log = {"calls": 0, "cancelled": 0}

    async def call():
        latency, result = steps[log["calls"]]
        log["calls"] += 1
        try:
            await asyncio.sleep(latency)
        except asyncio.CancelledError:
            log["cancelled"] += 1
            raise
        if isinstance(result, Exception):
            raise result
        return result

    return call, log


async def test_fast_call_makes_no_copy():
    call, log = fake((0.05, "ok"))
    assert await hedged(call, delay=0.2) == "ok"
    assert log["calls"] == 1


async def test_slow_call_is_beaten_by_copy():
    call, log = fake((5.0, "lenta"), (0.05, "copia"))
    start = time.perf_counter()
    assert await hedged(call, delay=0.1) == "copia"
    assert time.perf_counter() - start < 0.5
    await asyncio.sleep(0)
    assert log["cancelled"] == 1


async def test_fast_failure_triggers_copy_immediately():
    call, log = fake((0.01, RuntimeError("500")), (0.05, "copia"))
    assert await hedged(call, delay=10) == "copia"
    assert log["calls"] == 2


async def test_failed_copy_does_not_win():
    call, log = fake((0.3, "original"), (0.01, RuntimeError("500")))
    assert await hedged(call, delay=0.1) == "original"


async def test_all_failures_raise():
    call, log = fake((0.01, RuntimeError("a")), (0.01, RuntimeError("b")))
    try:
        await hedged(call, delay=10)
    except RuntimeError:
        return
    raise AssertionError("deveria ter falhado")


async def main():
    tests = [f for name, f in globals().items() if name.startswith("test_")]
    for test in tests:
        await test()
        print(f"ok  {test.__name__}")


if __name__ == "__main__":
    asyncio.run(main())
