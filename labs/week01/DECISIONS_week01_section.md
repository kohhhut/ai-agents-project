# Week 1: the stack, the first call, and what it costs

## Week 1

**Run conditions.** Everything below was produced on:

- machine: MacBook Air, Apple M4, 16 GB
- model: qwen3:4b-instruct
- served by: Ollama, one request at a time, locally
- date: [2026-09-29]

Every number in this file is meaningless without those four lines, so they are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the required model set (qwen3:4b-instruct and nomic-embed-text). OLLAMA_CONTEXT_LENGTH=8192 is set and 00_preflight.py is green.

Optional models: qwen2.5:7b, qwen3-vl:4b pulled

### 2. The first call

| | |
| finish reason | stop |
| prompt tokens | 24 |
| completion tokens | 45 |
| elapsed | 4.14 s |

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

If the finish reason were length instead of stop, my program would treat the answer as cut off: it would not pass it on as complete, and would either raise max_tokens or retry, and record the truncation in the trace. I control the prompt tokens directly (by what I send) and the completion tokens only indirectly (through the prompt and the max_tokens cap). The 4.14 s probably includes loading the model into memory on the first call; later warm calls are much faster (see section 4). A user feels the wait before the answer appears and the length of the answer.

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | 1/12 | 0.09 s |
| closed_short, t=1.0 | 1/12 | 1/12 | 0.09 s |
| open_short, t=0.0 | 1/12 | 1/12 | 1.02 s |
| open_short, t=1.0 | 5/12 | 10/12 | 1.02 s |
| open_list, t=0.0 | 1/12 | 1/12 | 1.05 s |
| open_list, t=1.0 | 11/12 | 12/12 | 1.21 s |
| open_reasoning, t=0.0 | 1/12 | 1/12 | 5.55 s |
| open_reasoning, t=1.0 | 12/12 | 12/12 | 6.55 s |

Temperature 0. I got 1 distinct answer in all four cells, and the recording also has 1 in every cell, so my machine agrees with it. At temperature 1.0 my counts differ from the recording in two cells (open_short 10/12 against 5/12, open_list 12/12 against 11/12), which is expected, because those runs are sampled and differ every time.

Which cell still returns a single answer at temperature 1.0, and why that one. closed_short. The correct answer is one or two tokens and the model puts almost all its probability on it, so sampling has nothing else to pick. The temperature did work; there was just no spread to sample from. Variation also grows with length: at temperature 1.0 the answers get less repeatable as they get longer, and the longest cell (open_reasoning) gave 12 different answers in 12 runs.

Which cells a test asserting exact string equality would pass on, and what that tells me. It would pass on the four temperature 0 cells and on closed_short at 1.0 (5 of 8 cells), and fail on the other three. So exact-match tests are only safe at temperature 0 or when the answer is tiny; for anything open-ended I have to test properties of the answer (format, required facts, length), not its exact string.

The sentence that carries into week 10. I can rely on getting the same output twice only when temperature is 0 or the answer is essentially a single forced token; at temperature 1.0 the chance of an identical answer falls quickly as the answer gets longer, so tests must check properties of an answer, not its exact text.

### 4. The cold start

- cold call: 1.02 s
- warm call: 0.1 s
- ratio: about 10.2

What this implies for a system that uses more than one model, and what I will do about it:

inside one request I would avoid alternating between models. I would group work by model, keep both resident if memory allows (checked with ollama ps), and warm each model at startup.

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier | 0.03352 | 3.2849600000000003 |
| large tier | 2.4912 | 244.13760000000002 |

Estimates against the price list dated [2026-09-29](0.17 EUR and 12.46 EUR per thousand calls on the small and large tier), not
measurements. Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why not the same one for both:

I would run the small tier nightly, because it is about 75 times cheaper and is enough to catch regressions. I would run the large tier before a release, where one run costs about 2.5 EUR and a more careful check is worth it. Not the same tier for both, because running the large tier every night would cost about 244 EUR for little extra information per night.

### Deferred
Nothing deferred: the full eight-cell variance sweep is done.
