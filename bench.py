import argparse
import asyncio
import random
import statistics
import time

import matplotlib.pyplot as plt

from hedged import hedged

PROMPT = "Explique em uma frase o que é latência de cauda."


async def fake_call():
    if random.random() < 0.05:
        await asyncio.sleep(random.uniform(8, 15))
    else:
        await asyncio.sleep(random.lognormvariate(0.4, 0.25))


async def measure(fn, n, concurrency):
    semaphore = asyncio.Semaphore(concurrency)

    async def one():
        async with semaphore:
            start = time.perf_counter()
            await fn()
            return time.perf_counter() - start

    results = await asyncio.gather(*(one() for _ in range(n)), return_exceptions=True)
    latencies = [r for r in results if not isinstance(r, BaseException)]
    return latencies, n - len(latencies)


def percentiles(latencies):
    q = statistics.quantiles(latencies, n=100)
    return {"p50": q[49], "p90": q[89], "p95": q[94], "p99": q[98], "max": max(latencies)}


def plot(base, hedge, delay):
    top = max(base + hedge)
    bins = [i / 4 for i in range(int(top * 4) + 2)]
    plt.hist(base, bins=bins, alpha=0.6, label=f"sem hedge (p99 {percentiles(base)['p99']:.1f}s)")
    plt.hist(hedge, bins=bins, alpha=0.6, label=f"com hedge (p99 {percentiles(hedge)['p99']:.1f}s)")
    plt.axvline(delay, linestyle="--", color="gray", label=f"delay do hedge ({delay:.1f}s)")
    plt.yscale("log")
    plt.xlabel("latência (s)")
    plt.ylabel("chamadas")
    plt.title("Hedged requests: a cauda longa some")
    plt.legend()
    plt.savefig("latencia.png", dpi=150, bbox_inches="tight")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--simular", action="store_true")
    args = parser.parse_args()

    if args.simular:
        call = fake_call
        concurrency = args.n
    else:
        from llm import ask
        call = lambda: ask(PROMPT)
        concurrency = args.concurrency

    counter = {"calls": 0}

    def counted_call():
        counter["calls"] += 1
        return call()

    print(f"1/2 sem hedge ({args.n} chamadas)...")
    base, base_errors = await measure(call, args.n, concurrency)
    delay = percentiles(base)["p90"]

    print(f"2/2 com hedge (delay = p90 = {delay:.2f}s)...")
    hedge, hedge_errors = await measure(lambda: hedged(counted_call, delay), args.n, concurrency)

    b, h = percentiles(base), percentiles(hedge)
    print(f"\n{'':6}{'sem hedge':>12}{'com hedge':>12}{'ganho':>9}")
    for key in b:
        print(f"{key:6}{b[key]:>11.2f}s{h[key]:>11.2f}s{1 - h[key] / b[key]:>9.0%}")

    extra = counter["calls"] - args.n
    print(f"\nchamadas extras: {extra} ({extra / args.n:.1%} de custo a mais)")
    print(f"erros: {base_errors} sem hedge, {hedge_errors} com hedge")

    plot(base, hedge, delay)
    print("gráfico salvo em latencia.png")


if __name__ == "__main__":
    asyncio.run(main())
