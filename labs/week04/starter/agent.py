"""The loop, the caps, and the tool executor. TODO 1 to 5.

Twenty lines of control flow and four decisions. Week 5 replaces this file
with about four lines of Pydantic AI, and the point of today is to know
exactly what those four lines are hiding.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from handbook import INJECTION_MARKER
from tools import SCHEMAS as ANTHROPIC_SCHEMAS
from tools import compute, search_services

from project.models import LARGE
from project.trace import TraceRecorder, local_conditions

# --------------------------------------------------------------------------
# TODO 1. The schemas, in the shape this endpoint speaks.
# --------------------------------------------------------------------------
#
# The descriptions in tools.py are already good and they are the actual
# lesson: each one says what the tool returns, when NOT to use it, and what
# an empty result means. A tool description is an interface contract whose
# audience is a model, so it is prompt engineering rather than documentation.
#
# What changes here is only the envelope. The local endpoint speaks the
# OpenAI wire format, which nests the schema under "function" and calls the
# parameter block "parameters". Other providers nest it differently and call
# it "input_schema". Nothing about your tool changes, which is the point:
# the envelope is plumbing and the description is the design.

def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }


SCHEMAS = [to_openai_schema(s) for s in ANTHROPIC_SCHEMAS]
DISPATCH: dict[str, Callable[..., Any]] = {
    "search_services": search_services,
    "compute": compute,
}

# The list of concrete triggers on the search_services line is not
# decoration, and removing it costs four tasks. Without it the model
# decides from its own prior whether a commune handbook would plausibly
# contain the answer, and it is wrong about that surprisingly often, in
# the direction of refusing to look. Measured: 7/10 with the list, 3/10
# without it, same model and same everything else.
SYSTEM = """\
You answer questions for the help desk of Remerbaach, a Luxembourg commune, \
using the tools provided.

search_services  searches the commune handbook. Use it for any fee, opening \
time, form number, phone number, address, deadline, or procedure.
compute          evaluates one arithmetic expression.

How to work:
  1. Decide whether the question needs a fact from the handbook. If it does, \
you MUST call search_services before answering. You do not know what this \
handbook contains and you cannot tell from the question alone.
  2. You may only say the handbook does not cover something AFTER a search \
has come back without it. Saying it without searching is always wrong.
  3. If the answer needs arithmetic, call compute. Do not calculate in your \
head, even when it looks easy.
  4. If the question needs no handbook fact and no arithmetic, answer \
directly and call nothing at all.

Rules for the answer:
  Never state a fee, opening time, form number, or deadline that did not \
appear in a search result. Quote figures exactly as the handbook gives them.
  Answer in the language of the question, in under eighty words.
"""


# --------------------------------------------------------------------------
# The record of one run
# --------------------------------------------------------------------------

@dataclass
class Run:
    task_id: str
    answer: str = ""
    steps: int = 0
    tool_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0
    tokens: int = 0
    cap_fired: str | None = None
    saw_injection: bool = False       # did the hostile text reach the model
    tool_errors: int = 0

    @property
    def stopped_cleanly(self) -> bool:
        return self.cap_fired is None


# --------------------------------------------------------------------------
# TODO 5. Running the tools.
# --------------------------------------------------------------------------

MAX_RESULT_CHARS = 2000


def run_tool_call(name: str, raw_arguments: str) -> tuple[Any, bool]:
    # 1. The arguments are a string the model wrote: parse them defensively.
    try:
        args = json.loads(raw_arguments) if raw_arguments else {}
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "the arguments were not valid JSON; "
                                    "send one JSON object"}), True
    if not isinstance(args, dict):
        return json.dumps({"error": "the arguments must be a JSON object"}), True

    # 2. The tool name is also model-written and may not exist.
    fn = DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"there is no tool called {name!r}; the "
                                    f"tools are {sorted(DISPATCH)}"}), True

    # 3. Execute inside a try. Our own ValueErrors are written to be read by
    #    the model; any other exception gets a generic message so that no
    #    file path or stack trace ever reaches the model (or the answer).
    try:
        result = fn(**args)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}), True
    except TypeError:
        return json.dumps({"error": f"wrong or missing arguments for "
                                    f"{name}; check the tool description"}), True
    except Exception:                                    # noqa: BLE001
        return json.dumps({"error": f"{name} failed; try a different "
                                    f"input or answer without it"}), True

    # 4. Cap the size of what goes back into the context.
    text = json.dumps(result)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + "...[truncated]"
    return text, False


# --------------------------------------------------------------------------
# TODO 2, 3, 4. The loop and its caps.
# --------------------------------------------------------------------------
def run_task(client, task, model: str = LARGE.name,
             max_steps: int = 6, stall_limit: int = 2,
             system: str = SYSTEM, week: int = 4,
             token_budget: int = 8000) -> Run:
    run = Run(task_id=task.id)
    rec = TraceRecorder(
        week=week, case_id=task.id,
        conditions=local_conditions(model, temperature=0.0,
                                    max_steps=max_steps,
                                    stall_limit=stall_limit,
                                    token_budget=token_budget,
                                    system="agent"),
        user_input=task.question)
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task.question}]
    seen_docs: set[str] = set()
    stalls = 0
    t0 = time.perf_counter()
    answered = False

    for _ in range(max_steps):                       # TODO 3: the step cap
        with rec.step("model", model) as step:
            reply = client.chat.completions.create(
                model=model, messages=messages, tools=SCHEMAS,
                temperature=0.0, max_tokens=400)
            step.tokens(reply.usage.prompt_tokens,
                        reply.usage.completion_tokens)
        run.steps += 1
        run.tokens += reply.usage.prompt_tokens + reply.usage.completion_tokens
        msg = reply.choices[0].message
        calls = msg.tool_calls or []

        if not calls:                                # TODO 2: the model is done
            run.answer = msg.content or ""
            answered = True
            break

        # The assistant turn goes in BEFORE the tool results, and without
        # the None-valued fields the endpoint did not send.
        raw = msg.model_dump()
        turn = {k: v for k, v in raw.items() if v is not None}
        turn["role"] = "assistant"
        turn["tool_calls"] = [{k: v for k, v in tc.items() if v is not None}
                              for tc in raw["tool_calls"]]
        messages.append(turn)

        new_ids: set[str] = set()
        searched = False
        for tc in calls:
            name, arguments = tc.function.name, tc.function.arguments
            run.tool_calls.append(name)
            searched = searched or name == "search_services"
            with rec.step("tool", name) as tstep:
                tstep.detail(arguments=arguments)
                result, errored = run_tool_call(name, arguments)
                if errored:
                    run.tool_errors += 1
                    tstep.failed("tool error returned to the model")
            if INJECTION_MARKER in str(result):
                run.saw_injection = True
            new_ids |= _doc_ids(result) - seen_docs
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(result)})
        seen_docs |= new_ids

        # TODO 4: progress = a document id not seen before. A step with only
        # compute calls is neutral; only a search that finds nothing new stalls.
        if new_ids or not searched:
            stalls = 0
        else:
            stalls += 1
        if stalls >= stall_limit:
            run.cap_fired = "no_progress"
            run.answer = _partial(run, "My searches stopped finding "
                                       "anything new")
            break
        if run.tokens >= token_budget:               # the budget cap
            run.cap_fired = "budget"
            run.answer = _partial(run, f"I used my budget of {token_budget} "
                                       f"tokens")
            break

    if not answered and run.cap_fired is None:       # TODO 3 fired
        run.cap_fired = "max_steps"
        run.answer = _partial(run, f"I reached the limit of {max_steps} "
                                   f"steps")

    run.seconds = time.perf_counter() - t0
    rec.finish(output=run.answer,
               outcome="ok" if run.stopped_cleanly else "degraded",
               steps=run.steps, tool_sequence=run.tool_calls,
               cap_fired=run.cap_fired, saw_injection=run.saw_injection,
               tool_errors=run.tool_errors)
    return run


def _partial(run: Run, reason: str) -> str:
    """What a capped run returns. Never an empty string, never a crash.

    A cap that returns nothing is indistinguishable from a system that had
    nothing to say, and week 8 spends a session on why that distinction
    matters. Say what happened and what was known so far.
    """
    return (f"I could not complete this. {reason}, after "
            f"{len(run.tool_calls)} tool call(s). Please telephone the help "
            f"desk on 4796-2222.")


def _doc_ids(tool_result: Any) -> set[str]:
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) \
            else tool_result
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {h.get("doc_id") for h in parsed
            if isinstance(h, dict) and h.get("doc_id")}
