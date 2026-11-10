# Arcus Research Evaluation

- Run: 2026-11-10T23:20:04.619068+00:00
- Model: `nvidia/nemotron-3-ultra-550b-a55b`
- Questions: 30

## Results

| Metric | Result | Target |
|---|---:|---:|
| Retrieval hit rate | 25/25 (100.0%) | ≥80% |
| Answers with no unsupported numbers | 30/30 | 100% |
| Exact not-found responses | 5/5 | 5/5 |
| Median latency | 2.31s | <4s |
| p95 latency | 14.79s | — |
| Answerable questions answered | 24/25 | — |
| API errors | 0 | 0 |

## Failures

- `meta-risk-1`: fell back to not-found (Uncited factual sentences: ['Meta also faces cybersecurity risks and is subject to laws and regulations relating to'])
