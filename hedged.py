import asyncio


async def hedged(call, delay):
    pending = {asyncio.create_task(call())}
    copies = 1
    error = None
    try:
        while pending:
            timeout = delay if copies == 1 else None
            done, pending = await asyncio.wait(pending, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                if task.exception() is None:
                    return task.result()
                error = task.exception()

            if copies == 1:
                pending.add(asyncio.create_task(call()))
                copies += 1

        raise error
    finally:
        for task in pending:
            task.cancel()
