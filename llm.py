import asyncio
import time

from anthropic import AsyncAnthropic

from hedged import hedged

MODEL = "claude-opus-5-5"

client = AsyncAnthropic()


async def ask(prompt):
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("o modelo recusou a pergunta")
    return next(block.text for block in response.content if block.type == "text")


async def main():
    prompt = "Explique em uma frase o que é latência de cauda."
    start = time.perf_counter()
    answer = await hedged(lambda: ask(prompt), delay=3)
    print(answer)
    print(f"\n{time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
