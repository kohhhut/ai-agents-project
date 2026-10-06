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
