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
sequenceDiagram
    participant C as Chamador
    participant H as hedged
    participant A as Chamada original
    participant B as Cópia

    C->>H: hedged(call, delay)
    H->>A: dispara
    alt responde antes do delay
        A-->>H: resposta
        H-->>C: resposta (1 chamada)
    else passou do delay ou falhou
        H->>B: dispara cópia
        par corrida
            A-->>H: ...
        and
            B-->>H: ...
        end
        H-->>C: primeira resposta com sucesso
        H->>A: cancela a perdedora
    end
```

Regras:

- A cópia só é disparada se a original passar do `delay` **ou** falhar.
- Vence a primeira chamada que terminar **com sucesso**; erro não vence corrida.
- Só lança erro se todas falharem.
- As perdedoras são canceladas no `finally`, em qualquer cenário.
