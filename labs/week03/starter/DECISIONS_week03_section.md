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