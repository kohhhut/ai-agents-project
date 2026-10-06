# Week 2: a structured-output extractor, measured

Copy this into your `DECISIONS.md` and fill it in.

---

## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: week02-zero-shot-v1 |
served locally | date: 2026-09-24 | scored on: my own machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: null
- due_date, when the message states only a relative expression: null
- quote, and what "verbatim" means in my scorer: the quote must occur in the message as a substring, character for character, with no normalisation
- what my scorer does with a record that failed validation: counts it wrong on every field

[ I count a record that failed validation as wrong on every field, so a broken answer stays in the ten and cannot make the score look better by disappearing. ]

### 2. Zero-shot, per field

| field | correct | of |
| category | 10 | 10 |
| urgency | 9 | 10 |
| due_date | 6 | 10 |
| quote | 10 | 10 |
| invalid records | 0 | 10 |

Zero-shot failures:

- REQ-01 due_date got '2026-09-15', expected null
- REQ-02 urgency got 'urgent', expected 'standard'
- REQ-05 due_date got '2026-09-30', expected null
- REQ-08 due_date got 'null' (the string), expected null
- REQ-10 due_date got '2026-09-30', expected null

4277 tokens, 22.5s over 10 documents.

My prediction, written before block 3: examples will help most on [due_date]
because [it is the weakest field in the zero-shot table, 6/10, and the misses are invented dates.]

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| EX-02 | French lift, urgent, "immediate" is not a date | category, due_date |
| EX-04 | "next week" is not a date, urgency info | due_date, urgency |
| EX-05 | French month name is a real date, 2026-09-30 | due_date |
| EX-01 | English, no date, not urgent because the person is not blocked | due_date, urgency |

| field | zero-shot | few-shot | move |
| category | 10/10 | 9/10 | -1 |
| urgency | 9/10 | 10/10 | +1 |
| due_date | 6/10 | 9/10 | +3 |
| quote | 10/10 | 7/10 | -3 |

Few-shot failures:

- REQ-03 quote is not a verbatim span
- REQ-04 quote is not a verbatim span
- REQ-06 quote is not a verbatim span
- REQ-08 category got 'access', expected 'hardware'
- REQ-10 due_date got '2026-09-30', expected null

8088 tokens, 30.4s over 10 documents. Invalid records: 0 in both runs.

### 4. What got worse

[ Quote fell from 10/10 to 7/10, and category from 10/10 to 9/10. On REQ-03, REQ-04, and REQ-06 the model copied a long span in the style of the examples and corrupted the ending, so the quote is no longer a verbatim substring. REQ-08 was hardware without examples and became access with them: the block has an access example and a facilities example, and no broken device. The invented dates on REQ-01 and REQ-05 disappeared, and the urgency error on REQ-02 was fixed. REQ-10 kept the same wrong date, 2026-09-30. On REQ-08 the date was fixed and the category broke, which is a new error, not the old one under another label. ]

### 5. What the examples cost

- extra input tokens per call: [ 364 ]
- per thousand calls: [ 364000 ]
- estimated euros per thousand calls on the small tier: [ 0.0728 ], against the
  price list dated [ 2026-08-10 ]. Estimate, not a measurement.

### 6. Ship it or not

[I would not ship the few-shot block yet. It moved due_date from 6/10 to 9/10 and urgency from 9/10 to 10/10, which is what the examples were for, but quote fell from 10/10 to 7/10 and category from 10/10 to 9/10. The extra 364 input tokens cost about 0.0728 EUR per thousand calls on the small tier, so cost is not the reason. Ten records are not enough to be confident. I would change my mind if, on a larger set, due_date stayed improved and quote stayed a verbatim span.]

### Sensitivity variant

Variant assigned: [ role ]. What I changed: [ I prepended "You are a senior service desk analyst." and nothing else. ]. What moved: [ nothing. Every field stayed at category 9/10, urgency 10/10, due_date 9/10, quote 7/10, and the per-language error counts stayed 3, 1, and 1. The sentence added about 8 input tokens per call.  ].


### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

 My scorer cannot tell a quote that supports the urgency decision from any other span that merely occurs in the message, because quote is checked only with in. It also cannot tell that 15/09/2026 and 2026-09-15 are the same day, because due_date is compared as a string. 

### Deferred

I measured only the role variant, because the lab assigns one variant. I did not run reordered, no_delimiter, or english_only.
