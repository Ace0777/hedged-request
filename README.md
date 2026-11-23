# hedged-request

## Arquitetura

```mermaid
flowchart LR
    bench["bench.py<br/>benchmark"] --> hedged["hedged.py<br/>hedged(call, delay)"]
    llm["llm.py<br/>ask(prompt)"] --> hedged
    bench --> llm
    llm --> api[("API da Claude")]
    tests["test_hedged.py<br/>chamadas falsas"] --> hedged
```

| Módulo | Responsabilidade |
|---|---|
| `hedged.py` | A técnica. Recebe qualquer chamada assíncrona e um `delay`; não conhece LLM. Só stdlib (`asyncio`). |
| `llm.py` | Cliente da Claude (`AsyncAnthropic`). `ask(prompt)` faz uma chamada e devolve o texto. |
| `bench.py` | Mede N chamadas sem e com hedge, usa o p90 medido como `delay`, reporta p50/p90/p95/p99, custo extra e gera `latencia.png`. |
| `test_hedged.py` | Testa `hedged` com chamadas falsas (`asyncio.sleep`): sem API, sem custo. |

### Fluxo do `hedged`

```mermaid
flowchart TD
    A[Dispara a chamada] --> B{Respondeu antes<br/>do delay?}
    B -- Sim --> R1[Devolve a resposta<br/>1 chamada, custo extra zero]
    B -- "Não (lenta ou falhou)" --> C[Dispara uma cópia<br/>as duas correm juntas]
    C --> D[Usa a primeira que<br/>responder com sucesso]
    D --> E[Cancela a outra]
```

Regras:

- A cópia só é disparada se a original passar do `delay` **ou** falhar.
- Vence a primeira chamada que terminar **com sucesso**; erro não vence corrida.
- Só lança erro se todas falharem.
- As perdedoras são canceladas no `finally`, em qualquer cenário.
