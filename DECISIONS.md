# Decisions
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


# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: week02-zero-shot-v1 |
served locally | date: 2026-10-06 | scored on: my own
machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: null The strings "", "null" and "none" are not accepted as "no date" and are scored wrong, because they are a different failure (wrong shape). REQ-04 returned the string 'null' in the zero-shot run.
- due_date, when the message states only a relative expression: null. "before the end of the month" or "tomorrow" is not a calendar date and the model must not compute one. A date in ISO 8601 (YYYY-MM-DD) is only for a stated calendar date, and DD/MM/YYYY is read as European. REQ-10 still got an invented date in both variants.
- quote, and what "verbatim" means in my scorer: the quote must be a substring of the original message, checked with Python's in. No lowercasing, no stripping punctuation, no whitespace tolerance. An empty quote is rejected explicitly, because "" in text is always true. REQ-07 failed zero-shot because the model wrote "Die" with a capital D where the message has "die".
- what my scorer does with a record that failed validation: it counts it in invalid and counts every field as wrong for that document. In both runs invalid was 0.

A scorer that skips the records it could not parse reports a number that improves as the model gets worse, so a failed record has to count as a miss.

### 2. Zero-shot, per field

| field | correct | of |
| category | 10 | 10 |
| urgency | 9 | 10 |
| due_date | 6 | 10 |
| quote | 9 | 10 |
| invalid records | 0 | 10 |

My prediction, written before block 3: I did not write a prediction before running it

Failures: REQ-01, REQ-08 and REQ-10 invented a due date where the gold is null (the dates were from 2024, so the model does not know today's date); REQ-04 wrote the string 'null'; REQ-02 got urgency urgent instead of standard; REQ-07 quote was not verbatim.

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-06 | The message names a printer but the problem is a window, so it is facilities, not hardware; "getting worse by the hour" shows urgent. | category, urgency |
| EX-04 | "next week" is a relative expression, so due_date is null; it is also the only example of the info label. | due_date, urgency |
| EX-05 | A date written in words in a French message ("30 septembre 2026") becomes 2026-09-30, so the block is not English only. | due_date |

| field | zero-shot | few-shot | move |
| category | 10/10 | 9/10 | -1 |
| urgency | 9/10 | 9/10 | 0 |
| due_date | 6/10 | 9/10 | +3 |
| quote | 9/10 | 10/10 | +1 |

### 4. What got worse

category went from 10/10 to 9/10. REQ-09 (a suggestion to publish the help desk opening hours on the intranet) was labelled facilities instead of other. It did not fail zero-shot. My hypothesis, not tested: "opening hours" reads like a building matter, and one of the three examples is a facilities case, so the examples may have pulled the label toward facilities. To check it I would look at the raw answer and rerun with a different example set.

Looking at the failure lines rather than the counts:

REQ-01, REQ-04, REQ-08 (due_date) and REQ-07 (quote) disappeared.
REQ-10 changed shape but was not fixed: zero-shot invented 2024-06-30, few-shot invented 2024-12-31 for "before the end of the month". It is still a relative expression turned into a date.
REQ-02 did not move: urgency is urgent in both runs, the gold is standard. The message has a deadline (15/09/2026) and the model reads a deadline as urgency. The examples did not touch that boundary.
One new error appeared (REQ-09). Net: 6 failures became 3.

### 5. What the examples cost

extra input tokens per call: 247
per thousand calls: 247,000
estimated euros per thousand calls on the small tier: about 0.05 EUR, against the price list dated 2026-08-10. Estimate, not a measurement.

Time for the ten documents was 17.3 s zero-shot and 17.5 s few-shot, so locally the extra input made almost no difference. Hosted, the 247 tokens are paid on every call.

### 6. Ship it or not

I would ship the few-shot variant for now. Evidence: due_date went from 6/10 to 9/10 and quote from 9/10 to 10/10 for 247 extra input tokens per call, and the failures went from 6 to 3. But this is ten records, so one record is ten points, and the category regression (REQ-09) and the invented date on REQ-10 show the examples did not fix everything. What would change my mind: if the category drop repeats on the larger gold set in week 10, or if a variant with one more example (a suggestion labelled other, a relative deadline labelled null) removes both remaining errors for a similar token cost.

### Sensitivity variant

### Sensitivity variant

Variant assigned: role. What I changed: prepended "You are a senior service desk analyst." to my few-shot prompt, nothing else. What moved: due_date went from 9/10 to 8/10 and quote from 10/10 to 9/10; category and urgency did not move. Field errors in the English documents went from 2 to 4 (5 documents), French stayed at 1 (3 documents) and German at 0 (2 documents). The sentence costs about 11 more tokens per call (6535 against 6423 over ten documents, prompt plus completion). Temperature is 0, so the difference comes from the sentence and not from randomness, but it is two field errors on ten records, so I do not claim that a persona makes the extractor worse in general. What it shows is that a sentence no reviewer would flag changed the output on this set and bought nothing here.

### The gold set

Ten cases written to artifacts/goldset.json, tagged by language.

One thing my scorer cannot currently detect: whether a quote that appears in the message actually supports the urgency decision, or is complete. It only checks that the string is a substring of the source, so a quote cut off mid-word (the recording has one ending in "repari" for a message that ends "repariert") or an irrelevant sentence still scores as correct.

### Deferred

Nothing deferred

# Week 3: a router in front of the extractor

## Week 3

**Run conditions.** classifier model: qwen3:4b-instruct | answering model: qwen3:4b-instruct | temperature: 0.0 (0.7 for voting) | served locally | date: 2026-10-12 | scored on: my own machine 

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | Log a ticket and act, because something is broken, missing, or needed; if the message also asks a question, the action still makes it a request. |
| info | Answer with information only, because the sender asks about a service, a procedure, an opening time, or a form, and nothing has to be logged, fixed, or chased. |
| status | Report the state of something the sender already submitted, including a chase with no reference number, as long as the sender is not complaining about how it was handled. |
| complaint | Acknowledge and escalate dissatisfaction with the service, with how something was handled, or with how long it took; if an unresolved fault is reported too, acknowledge the handling first. |
| other | Redirect mail that is not help-desk work: a matter for another department, advice the help desk cannot give, spam, or an instruction aimed at the system rather than at a person. |

My convention for the four ambiguous queries (Q-13, Q-16, Q-18, Q-24): the route is decided by what the help desk must do first. A chase without a complaint is status (Q-13). A fault report plus a complaint about the handling is complaint, because the reply must acknowledge the handling first (Q-16, Q-18). A fault report plus a procedural question is request, because the action outranks the question (Q-24). I wrote this before measuring.

Do my definitions match the ones in `queries.py`? Not word for word, but they encode the same boundary rules as AMBIGUITY_NOTE, so my accuracy is measured under the same convention as the gold labels. The classifier alone got all four ambiguous queries as gold; after the policy 3 of 4 (Q-16 was overridden).

### 2. The policy layer

Before choosing the threshold I looked at the confidence values in the shipped recording (0, 0.95, 0.98, 0.99, 0.999), not at my own live run. On my live run the values were min 0.00, max 1.00, 4 distinct across 24 queries (0.0, 0.98, 0.99, 0.999).

- confidence floor: 0.9, because in the recording the small model is almost always above 0.95, so 0.9 only catches a call that gives up (confidence 0).
- evidence check: if the span is empty or not an exact substring of the message, the decision is rejected, because a router that invents its justification cannot be audited.
- safe default: info, because that specialist only answers and is forbidden to state facts, so a wrong answer is the easiest to undo; request logs a ticket and complaint escalates to a human.

How often each check fired: below_threshold 2 (Q-22, Q-23), evidence_not_verbatim 2 (Q-02, Q-16), invalid_decision 0.

The classifier alone scored 22/24, the routed system 18/24. All four policy firings overrode a correct decision, so the policy cost 4 points. The two kinds of firing behave differently:

- The floor is a real signal, but only for one kind of message. Both messages below 0.9 (an instruction aimed at the system and spam) got confidence 0.0, and both were correctly `other`. It does not see subtle errors: the two wrong routes (Q-20, Q-21) had confidence 0.99.
- The safe default is wrong for exactly those messages. `info` is easy to undo, but it is not where an injection or spam belongs; `other` would have been the right destination for both.
- The evidence check rejected a correct request (Q-02) and a correct complaint (Q-16). I did not inspect the rejected spans, so I do not know whether the model paraphrased them or changed accents.

### 3. Route accuracy (scored on applied_route, what the sender actually got)

| route | correct | of |
| request | 6 | 7 |
| info | 5 | 5 |
| status | 4 | 4 |
| complaint | 3 | 4 |
| other | 0 | 4 |

Overall 18/24. Excluding the four ambiguous: 15/20.

Confusion pairs, with direction:

| gold | applied | count |
| other | info | 4 |
| request | info | 1 |
| complaint | info | 1 |

Every error points into info. The route carrying most of the error is other (0/4). Of the 6 misses, 2 are classifier errors and 4 are policy overrides:

- Q-20 (subletting law) and Q-21 (property tax) were sent to info by the classifier itself, because "asks about a service" fits any question. The fix is a definition, not a prompt: info has to say the service must be one the help desk provides, and other has to name legal, tax and other-department questions.
- Q-22, Q-23 (confidence 0.0) and Q-02, Q-16 (evidence not verbatim) were correct decisions overridden by the policy. The fix is the policy: the safe default and the evidence check, not the prompt.

### 4. What routing cost

- monolith: 10768 tokens over 24 queries, 43.8 s
- router: 13923 tokens over 24 queries, 95.4 s
- the classifying call alone: 9307 tokens, which is 67 per cent of the routed total

I predicted that the classifier would account for approximately 50-60% of total token usage, with an estimated range of 55–70%, before measuring it.

The classifier prompt carries every route definition on every call, and each specialist carries only its own, so the cheap step is two thirds of the tokens. Overall the router costs 29 per cent more tokens and 2.2 times the time of the monolith.

The monolith is a fair opponent: it gets the same five definitions, the same model and temperature, and an instruction for each kind. It only lacks specialization. The starter scores routes only for the router, so I compare cost against the monolith, not accuracy.

### 5. What routing bought

The complaint specialist can be forbidden to promise a fix or a date, and the info specialist can be forbidden to state any opening time, fee or form number. The monolith cannot be given those instructions, because for a request it has to log a ticket and for a status chase it has to talk about the state of the work.

Would I ship the router: not on accuracy. Evidence: 18/24 routed against 22/24 for the classifier alone; with 24 queries and 4-7 per route one query moves a route by 15-25 points; and +29 per cent tokens and 2.2x time. Only the guarantees on the specialists justify it. What would change my mind: a policy that does not turn correct decisions into wrong ones (for example a different destination for confidence 0 and a looser evidence check), and a larger gold set with a monolith scored on routes as well.

### 6. Stretch variant

Variant assigned: both (model routing and voting).

Model routing. Prediction written before running: SMALL wins.

| | qwen3:4b-instruct | qwen2.5:7b |
| routed (applied) | 18/24 | 17/24 |
| excluding ambiguous | 15/20 | 15/20 |
| classifier alone | 22/24 | 19/24 |
| evidence verbatim | 22/24 | 20/24 |
| confidence range | 0.00-1.00, 4 distinct | 0.80-1.00, 3 distinct |
| resident memory | 3.9 GB | 5.0 GB |

SMALL won, by 3 routes before the policy and 1 after it. It is smaller, cheaper and more faithful at copying spans, so for classification a larger model is not better.

Voting (3 samples at temperature 0.7, majority): 19/24, 16/20 excluding ambiguous. The votes disagreed on no query, including the four ambiguous ones, so voting did not detect the ambiguity either. 72 calls instead of 24, 175.5 s. A poor buy: it triples the cost of the cheap step and tells me nothing the single call did not.

### The gold set

`artifacts/goldset.json` now holds 34 cases: 10 from week 2 and 24 added today, with the four ambiguous ones tagged `ambiguous`. Loaded from my own file (source: own).

### Definition I would rewrite first

info. I would add that the service must be one the help desk itself provides, and move legal, tax and other-department questions explicitly into other. I expect other->info to drop from 2 classifier errors (Q-20, Q-21) to 0, with no change to the other four routes.

### Deferred

Week 2 extractor wired behind the request route (homework). A live rerun with a changed safe default or evidence check, to measure how much of the 4-point policy loss comes back.