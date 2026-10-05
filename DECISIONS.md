```text
1. MOTIVATION
   I wanted to turn vague feature requests into a scope someone
   could review. The discussion should explain why a choice was
   accepted, changed, rejected, or left open.
                         |
                         v
2. HOW I FIRST THOUGHT ABOUT IT
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
   ├── Build an SME-reviewed golden dataset
   |   I would work with subject-matter experts to create vague test
   |   requests based on the system context. Each scenario would
   |   include expected concerns, acceptable scope decisions,
   |   unresolved dependencies, and reasonable stopping conditions.
   |   This would give us a reference for judging reasoning quality,
   |   without assuming there is only one correct proposal.
   |
   ├── Use an LLM judge to improve prompts iteratively
   |   After each evaluation run, an LLM judge would compare the
   |   dialogue and final report against the reference criteria.
   |   It would identify failures with supporting message references
   |   and propose revised prompts for the three agents.
   |
   |             Run → Judge → Revise prompts → Run again
   |
   |   I would retain a revision only when it improves measured
   |   performance without weakening other behaviors. SMEs would
   |   review the judge's assessments, and separate, untouched
   |   scenarios would test whether improvements generalize.
   |
   ├── Test behavioral boundaries and temperature
   |   I would strengthen and compare instructions about when the
   |   Proposer should defend or revise, when the Critic should
   |   challenge or accept, and what the Summarizer may claim.
   |   I would vary each agent's temperature separately and repeat
   |   runs to measure consistency, premature agreement, unnecessary
   |   objections, and report accuracy.
   |
   └── Compare models and explore weight fine-tuning
       I observed the Proposer accepting criticism too readily in
       some runs. I would compare pretrained models under the same
       evaluation conditions to separate model effects from prompt
       effects. These observations do not establish model age,
       size, or RLHF as the cause.

       If prompt improvements remained insufficient, I would
       fine-tune an open-weight model using SME-reviewed dialogues
       derived from the golden dataset. Training examples would
       demonstrate justified defence, revision, and stopping.
       Evaluation cases would remain outside the training data.
       I would compare quality, inference cost, and maintenance
       against the existing prompt-only approach.
```

Research reference: [Anthropic’s study of sycophancy](https://www.anthropic.com/research/towards-understanding-sycophancy-in-language-models).

