> **Writing note:** I used AI to help write and arrange my thoughts and assumptions into a vertical flow, like a progress bar showing how my thinking developed.

```text
1. MOTIVATION
   I wanted to turn vague feature requests into a scope someone
   could review. The discussion should explain why a choice was
   accepted, changed, rejected, or left open.
                         |
                         v
2. HOW I FIRST THOUGHT ABOUT IT
   When I saw the vague request, my first thought was, the agents
   could easily fill the gaps with their own assumptions. Then
   those assumptions might become part of the scope without anyone
   questioning them. I wanted to make them visible first.

   So my idea was, let the Proposer make a choice and explain why.
   Then let the Critic question it and explain what could go wrong.
   Even the Critic needs a reason for its objection. Otherwise it
   could keep asking for changes without making the proposal any
   better.

   For me, each round should settle something useful. Maybe we
   change the proposal, keep the original choice with a good reason,
   or say this part depends on a human decision. Just getting both
   agents to agree is not enough.

   Some answers also have to come from people. If an organizational
   policy was never given, another round cannot make that policy
   known. That thinking helped me decide what should stay
   conditional and when the discussion should stop.

   I thought about how people debate: someone puts forward an idea,
   someone questions it, and both work toward a better decision.

   I expected two agents with different responsibilities to bring
   that kind of discussion into the system.
                         |
                         v
3. RESEARCH AND EARLY EXPERIMENTS
   |
   ├── Agreeing too easily
   |   Research suggested that training with human feedback can
   |   encourage agreement. I also saw the Proposer readily accept
   |   criticism. I considered training, prompt wording, and model
   |   limitations as possible causes, but did not isolate them.
   |   I could not attribute the behavior to the model's age.
   |
   ├── Trying anti-sycophancy prompts
   |   I tried asking the agents to resist agreement more strongly.
   |   The prompts felt too aggressive without making the discussion
   |   more useful.
   |
   ├── Exploring first, then narrowing
   |   I considered exploring several interpretations and letting
   |   the Critic remove weak options. The current system works
   |   with one proposal that develops through repeated reviews.
   |
   └── Considering temperature
       I considered changing temperature but focused on the prompts.
       I did not run enough comparisons to judge its effect.
                         |
                         v
4. WHAT I LEARNED
   I needed clear reasons for changing a position or keeping it.

   Too little criticism could let weak assumptions pass.
   Too much criticism could keep expanding the work.
   Too much resistance could make the Proposer ignore valid concerns.

   That balance shaped the responsibilities of both agents.
                         |
                         v
5. HOW I BUILT IT
              Request + system context
                         |
                  PYTHON REFEREE
                         |
                  Proposer ↔ Critic
                         |
                    Summarizer

   The referee manages turns, accepted messages, challenge IDs,
   validation, logs, budgets, and stopping rules.
   The agents decide whether the arguments are convincing.
                         |
                         v
6. WHAT THE RUNS REVEALED
   |
   ├── Some details sounded more certain than they were
   |   A proposal justified a 90-day threshold without supporting
   |   context. I made the prompts distinguish facts, assumptions,
   |   and proposed choices.
   |
   ├── The Critic asked for information neither agent could obtain
   |   I asked it to explain what another exchange could actually
   |   resolve and leave external decisions as explicit conditions.
   |
   ├── The Critic gave the same challenge conflicting statuses
   |   I kept checks that reject these contradictions after limited
   |   correction attempts.
   |
   ├── The final report sometimes overstated agreement
   |   I supplied exact message IDs and recorded stopping facts.
   |   Agreement needs evidence from both agents. Still, the
   |   placeholder-policy contradiction showed that valid references
   |   do not guarantee an accurate report.
   |
   └── Longer discussions created other problems
       Responses could be truncated, history grew, and repairs used
       calls needed for the report. I increased response and repair
       headroom while keeping configurable limits.
                         |
                         v
7. HOW THE PROMPTS NOW WORK
   |
   ├── PROPOSER
   |   Choose an interpretation and explain its scope, assumptions,
   |   conditions, and success criteria. Respond to criticism by
   |   defending, revising, or conceding, with reasons. Carry each
   |   revision through the whole proposal.
   |
   └── CRITIC
       Explain the specific concern, its consequence, and what would
       address it. Separate blockers from optional improvements.
       Accept supported defences and actual revisions. Identify useful work
       for the next exchange.
                         |
                         v
8. CONFIDENCE AND STOPPING
   |
   ├── Confidence
   |   Each agent is prompted to rate five areas from 0–4.
   |   Score = their total × 5, capped at 60 when agreement is blocked.
   |   Python checks the range, not the calculation.
   |   The scores explain uncertainty; they do not decide when to stop.
   |
   └── Termination
       Completed: after at least two rounds, the Critic gives a valid
                  completion signal and has no agreement blockers.
       Stalled:   after at least two rounds, a blocker remains and
                  the Critic explains why another exchange cannot help.
       Capped:    the round limit is reached without either signal.
       Error:     execution or validation prevents progress.

       Valid completion or stall wins on the final allowed round.
       Completion means the scope is ready to document; some human
       decisions may still be needed before implementation.
                         |
                         v
9. WHAT I WOULD DO WITH MORE TIME
   |
   ├── Let the Critic think independently first
   |   Give it the original request before showing the Proposer's
   |   answer. See whether it catches issues that it misses when
   |   following the Proposer's interpretation.
   |
   ├── Check whether the Proposer follows evidence or confident wording
   |   Present valid and invalid objections in both polite and
   |   forceful language. It should accept useful criticism and
   |   defend sound decisions, regardless of tone.
   |
   ├── Ask the Critic to explain what could actually go wrong
   |   Instead of saying "access control is unclear," ask for a
   |   concrete failure scenario. This makes the concern easier
   |   to understand and the proposed fix easier to evaluate.
   |
   ├── Check whether stopping was the right decision
   |   In a separate test, allow one extra round after completion.
   |   See whether it discovers something important, repeats the
   |   discussion, or introduces unnecessary requirements.
   |
   ├── Change one fact and check whether the decision changes appropriately
   |   For example, replace an unknown policy with an explicit
   |   restriction. Also paraphrase the same request to check that
   |   harmless wording changes do not produce substantially
   |   different scope.
   |
   ├── Test the LLM judge before letting it improve prompts
   |   Give it reports with deliberately missing conditions,
   |   incorrect citations, or false claims of agreement. Check
   |   whether it catches these mistakes, and whether changing
   |   the order of reports affects its judgment.
   |
   └── Compare the debate against a simpler approach
       Let a single model draft and review the scope using a similar
       token budget. This would show where the two-agent discussion
       improves quality enough to justify the extra calls.
```

Research reference: [Anthropic’s study of sycophancy](https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models).

