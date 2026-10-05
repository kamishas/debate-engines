# Evaluation and refinement record

Initial evaluation on October 4, 2026 (America/New_York); the approved prompt-only follow-up is recorded separately below. Run folder names and stored timestamps use UTC, so the final initial sample has an October 5 UTC prefix. These are genuine Anthropic API runs using the locally configured key and the same pinned Haiku model for all three roles. No assessment PDF was sent to the API.

## Offline verification

**45 tests passed**, followed by successful Ruff lint and formatting checks. The installed CLI was also exercised. Tests use synthetic fixtures and an in-process SDK HTTP transport; they do not establish reasoning quality or summary fidelity.

Coverage includes minimum rounds, completion at the cap, stalled/capped/error outcomes, input validation, confidence ranges, bounded output repair, transient retry exhaustion, context and call limits, incremental logging, output-write failure, summary ordering/failure, partial reports, exact confidence copying, evidence references, and explicit active challenge IDs. Optional objections are not mandatory Proposer responses.

## Initial usable sample runs

| Scenario | Rounds | Deliberation | Report | Calls | Latest confidence (Proposer / Critic) |
| --- | --- | --- | --- | --- | --- |
| Right contact | 3 | capped | succeeded | 9 | 72 / 72 |
| Engagement history | 3 | completed | succeeded | 8 | 77 / 78 |
| Cold relationship | 3 | completed | succeeded | 9 | 70 / 72 |

All three include both main agents, a separate Summarizer call, confidence with reasons and uncertainties, a readable transcript, machine-readable exchanges, metadata, and final JSON. Scores are self-reported judgments, not probabilities or evidence of correctness.

- Right contact: [final JSON](sample_runs/right-contact/final.json), [transcript](sample_runs/right-contact/transcript.md), [metadata](sample_runs/right-contact/metadata.json).
- Engagement history: [final JSON](sample_runs/engagement-history/final.json), [transcript](sample_runs/engagement-history/transcript.md), [metadata](sample_runs/engagement-history/metadata.json).
- Cold relationship: [final JSON](sample_runs/cold-relationship/final.json), [transcript](sample_runs/cold-relationship/transcript.md), [metadata](sample_runs/cold-relationship/metadata.json).

Each sample directory also has exchanges.jsonl and input.json. Original logs remain under runs/. sample_runs/index.json records all attempts and actual token usage. Final-document schemas, supporting message existence, and latest confidence values were rechecked against the copied accepted exchanges.

**Structural checks passed. Semantic fidelity is not fully solved.** The reports are reviewable assessment samples, not approved product specifications.

## What the real traces showed

The contact proposal became concrete through a primary/secondary contact model, role-based filtering, and designation metadata. The final report correctly preserves a disagreement about mandatory secondary contacts, separates a proposed 60% adoption target, and identifies human decisions. The cap remained capped; it did not become consensus.

The history case revised broad access into authorized and retained history, excluded personal contact details from the country view, and explicitly made the view read-only. In r3-critic, the Critic distinguished scope documentation from implementation readiness and signalled complete while retaining access-policy and technical-verification questions. The report preserves those conditions and the challenged queryability assumption.

The final cold case demonstrates defence and revision. In r2-proposer, C1–C5 defend leaving activity definitions, thresholds, exemptions, routing, and confidentiality workflow to stakeholders; the Proposer explicitly declines to invent a 90-day threshold. C6–C8 produce revisions for adoption measurement, fatigue monitoring, and audit detail. The last Critic accepts the post-launch-governance revision and signals completion because another exchange cannot supply missing stakeholder information.

An earlier contact attempt also contains a clear defence of excluding notifications (r2-proposer/C5), accepted by r2-critic. That trace later suffered a protocol error and remains labelled accordingly. A separate weak-criticism probe was unnecessary because genuine example exchanges already demonstrated accepted defence.

Both completion and capped termination occurred live. A justified stalled outcome is covered offline, but was not observed in these live runs.

## Failures retained and fixes made

The initial contact run hit a 4096-token output limit. Including the truncated response in a repair also exceeded its 100000-byte local context bound; summarization failed as well. The engine retained raw responses and reported error instead of truncating history or fabricating success. Output headroom was raised to 8192 and local input headroom to 250000 bytes.

Subsequent attempts exposed challenge-ID errors: assessing a newly invented challenge as a previous response, renaming an unresolved challenge, or responding again to resolved challenges. Generic repair instructions were insufficient. The payload now supplies active IDs explicitly. Validation identifies all missing/unexpected IDs and contradictory dispositions in one correction. Optional objections can be omitted by the Proposer. This changes protocol handling, not Python's judgment of arguments.

The Summarizer sometimes appended labels such as '(C1)' to message IDs or cited only one role for agreement. Reference validation caught these. Feedback now identifies every affected field in one repair, instead of disclosing errors one at a time.

One cold run reached capped after three rounds but exhausted its nine-call budget before summary repair. Its deliberation outcome stayed capped and report status became failed. A fresh cold run, with a twelve-call budget, completed and generated a report. No interrupted or failed run was resumed.

The retained failure samples are initial-contact-budget-failure, contact-protocol-failure, history-protocol-failure, cold-protocol-failure, and cold-call-budget-failure. Some have valid partial final documents; none is relabelled as a successful deliberation.

## Budget and actual usage

The initial plan used three rounds, twelve attempts, and 4096 output tokens per attempt. After the first sizing failure, three cases were run with three rounds, nine attempts, and 8192 output tokens. Protocol-fix reruns used the same bounds. Only the final cold rerun increased the attempt cap to twelve, leaving its three-round limit unchanged. Retries, repairs, and summarization all consume the same hard call cap.

Across eight recorded attempts: **66 model calls, 853548 reported input tokens, and 221430 reported output tokens**. These are API usage counts, not a billing assertion. There were five failed attempts before the three usable sample reports. The twelve-call final run used nine calls. No automatic outer retry loop or model-family fallback was used.

## Next prompt and termination refinement

These proposals were recorded after the initial eight attempts. The later approved prompt edits and their single-run evidence review are described below; original traces remain unchanged.

1. **Proposer grounding.** Require proposed numeric targets and proposed stakeholder ownership to be labelled explicitly. Earlier cold output justified a 90-day threshold as common practice and assigned Operations leadership an exemption authority; the supplied context did not establish either. The final cold trace handles the threshold better, but governance owners and performance targets still require human confirmation. Different runs varied; this is not proof that protocol fixes caused better reasoning.
2. **Critic consistency and useful continuation.** The contact case repeatedly requested external policy or organizational evidence, which another model exchange could not obtain. Ask the Critic to name the next issue that can actually be resolved from available information. When only bounded human decisions remain, assess documentation readiness; when substantive disagreement remains and cannot progress, explain a stall. Keep minimum rounds and cap precedence unchanged.
3. **Confidentiality contradictions.** In cold-protocol-failure, r2-proposer described both suppressing an alert involving an inaccessible contact and showing restricted-contact activity metadata; r2-critic accepted both. A concrete consistency check in the Critic prompt should challenge this conflict and whether even record-existence metadata may be disclosed. The later cold report leaves withheld/redacted/escalated behavior as a human decision, but one better run does not remove this regression case.
4. **Summary evidence precision.** The final cold report's agreed audit-trail item cites r1 messages even though acknowledgment/action logging was elaborated in r2-proposer/C8. Its A2 assumption is labelled accepted with r1 references, which compresses a challenge-and-revision history. Existing references are not necessarily sufficient evidence. Ask for the smallest relevant supporting set including the revision and acceptance, and preserve challenged/revised dispositions. Keep the genuine output unchanged as an evaluation case.
5. **Termination evaluation.** Compare completed, stalled, and capped cases on a small reviewed set rather than raising the round cap to force apparent success. Confidence thresholds and text-change counts remain unsuitable substitutes for argument review.

Before submission, review every material agreement and assumption against the cited exchanges and revise DECISIONS.md in your own words. Schema validity and these limited live examples do not guarantee faithful scoping across new requests.

## Approved termination prompt refinement and evidence review

The user approved the exact prompt wording before application. The Proposer now explicitly checks consistency across included, excluded, and conditional scope, assumptions, and criteria after a revision. The Critic now explicitly checks contradictions before completion, identifies useful work possible from the available information before continuing, and distinguishes substantive disagreement from an agreed condition requiring a later human decision. These edits build on the previously approved confidence rubric.

Only the two agent prompts changed in the implementation. All Python source hashes were checked before and after the edits; schemas, validation, termination rules, and orchestration are unchanged. The existing **45 offline tests passed**. The installed package loaded the approved text, and the saved API requests contained those exact prompts. Tests verify integration and control behavior, not prompt effectiveness.

### One bounded live run

The same right-contact request and Government CRM context were used with `claude-haiku-4-5-20251001`. The run was limited to four rounds, twelve provider attempts, 8192 output tokens per attempt, 250000 input bytes, one repair per logical turn, and one transient retry. Exactly one fresh run was made; there was no outer rerun after failure.

Run: `20261005T020448Z-359b8080`, October 5, 2026, 02:04:48–02:11:04 UTC (October 4 local).

| Item | Observed result |
| --- | --- |
| Deliberation | `error` during the second Critic turn |
| Completed rounds | 1; the second Proposer turn was accepted, but neither second-round Critic attempt was accepted |
| Report | `succeeded`, with `partial: true` |
| Provider calls | 7 of 12 allowed |
| Reported input / output tokens | 89614 / 30744 |
| Repairs | One Critic repair and one Summarizer repair |

Evidence: [metadata](runs/termination-prompt-review/20261005T020448Z-359b8080/metadata.json), [full transcript](runs/termination-prompt-review/20261005T020448Z-359b8080/transcript.md), [raw events](runs/termination-prompt-review/20261005T020448Z-359b8080/exchanges.jsonl), and [partial final report](runs/termination-prompt-review/20261005T020448Z-359b8080/final.json).

### Findings

1. **The bounded failure path worked.** Call 4 duplicated prior challenge-assessment IDs. Its one repair, call 5, marked C2 and C3 resolved while retaining them as outstanding challenges. Validation rejected both attempts and stopped with `error`, rather than manufacturing completion or consuming the remaining rounds. Only `r1-proposer`, `r1-critic`, and `r2-proposer` entered the accepted dialogue.
2. **The consistency instruction was not fully followed.** In `r2-proposer`, the response to C1 says ranking has moved to conditional scope, with neutral ordering until criteria are established. The included scope still unconditionally lists filtering and ranking. Neither rejected Critic attempt identified this cross-field inconsistency; both treated the ranking response as resolving C1. Those rejected attempts are diagnostic evidence, not accepted deliberation.
3. **Requests for unavailable organizational work persisted.** The first accepted Critic response partly requested stakeholder clarification. The rejected repair went further: C2 asked the Proposer to commit to obtaining access-policy documentation on a timeline, C4 requested a CRM data audit, and C3 requested stakeholder interviews. Its next-exchange explanation blurred organizational work with progress possible in another model turn. The prompt instruction alone did not eliminate this behavior in this sample.
4. **The partial report has a remaining fidelity defect.** The initial Summarizer response used decorated rather than exact message IDs and omitted disputed scope despite outstanding blockers. Its repair passed the existing schema/reference checks and copied the exact latest confidence values. However, `decision.summary` incorrectly associates the protocol error with the first-round termination rule. The authoritative top-level `termination_reason` correctly records the contradictory C2/C3 dispositions. The actual failure was in the second Critic turn, not an attempted first-round stop.

**Conclusion:** the approved edits are installed, and the existing validation, bounded repair, logging, and partial-report paths operated as designed. This run did not reach a valid completion or stall decision, so it cannot establish improved stopping timing. It also exposes continuing prompt-adherence and summary-fidelity weaknesses. The initial proposal differs from the earlier contact run, so this is not a controlled before/after comparison and does not establish that the prompt edits caused the failure. No additional prompt or code changes were made to obtain a cleaner result.

## Approved report-quality refinement and frozen-dialogue evaluation

This follow-up changes the Summarizer payload, its prompt, and one report validation rule. The Summarizer receives the full accepted dialogue, an exact message ID/role/round index, and the authoritative termination outcome, reason, and completed-round count. It no longer receives the main agents' round instruction or active-challenge contract. The prompt asks for evidence before classification, preservation of unresolved conditions and contradictions, and accurate explanation of recorded execution facts. The final prompt also includes a worked example distinguishing agreement on a restricted-record placeholder from permission to disclose record existence.

The validation change allows an outstanding agreement blocker to be represented in either `disputed_scope` or `unresolved_scope`; an external dependency is not necessarily a disagreement between agents. Both sections being empty still fails when the latest accepted Critic has a blocker. This is a presence check, not a semantic check that every blocker is covered. Existing reference and both-role agreement checks remain in place. Schemas, termination rules, and the Proposer/Critic prompt text are unchanged.

### Offline checks

**53 tests passed**, with Ruff lint and formatting checks passing. Eight added test cases cover the isolated Summarizer payload, authoritative capped/error facts and exclusion of rejected turns, both allowed blocker categories, rejection of empty blocker coverage, and agreed-versus-proposed criteria with only Proposer evidence. These tests establish orchestration and validation behavior, not semantic reliability.

### Evaluation method and budget

Three existing right-contact dialogues were frozen: a completed run with a placeholder-policy contradiction, a capped run whose original report failed evidence validation, and an error run whose original partial summary misstated the failure cause. Only the Summarizer was called; Proposer/Critic responses and termination outcomes were not regenerated. The one-off [evaluation helper](runs/report-quality-review/evaluate_summary.py) reuses the production summarization/validation path and stores separate outputs. It is not a production resume feature.

All calls used `claude-haiku-4-5-20251001`, full accepted dialogue, 8192 output tokens per attempt, 500000 input bytes, and no provider retries. The initial prompt pass used two calls per case (one generation and one validation repair). After semantic review exposed the remaining placeholder inconsistency, a short worked example was added to the prompt. The final pass allowed exactly one call per case with no repair, staying within the approved total of **9 provider calls**. Production repair settings were not changed. Different repair allowances mean the two passes' report-success counts are not comparable reliability estimates.

Total reported usage: **207202 input tokens and 46291 output tokens**. SHA-256 comparisons confirmed that all files in the three original run directories remained unchanged. Each evaluation preserves the actual prompt, response, validation results, source hashes, and call usage in its logs.

### First pass: structural success did not establish fidelity

| Frozen source | Separate evaluation | Calls | Observed result |
| --- | --- | --- | --- |
| Completed: `20261005T023613Z-9ac1e50b` | [Report](runs/report-quality-review/placeholder/20261005T030646Z-5f335af3/final.json) | 2 | Passed after repair, but still called the placeholder agreed while retaining the disclosure-policy question. |
| Capped: `20261005T021432Z-b7e64989` | [Report](runs/report-quality-review/capped/20261005T030647Z-6c15feba/final.json) | 2 | Passed after repair; C2/C5 remained unresolved. The sixth criterion still claimed agreement using r1 citations, although explicit fallback acceptance appears in r2-critic and rollout qualifications appear later. |
| Error: `20261005T020448Z-359b8080` | [Report](runs/report-quality-review/error/20261005T030647Z-e61e7198/final.json) | 2 | Passed after repair; correctly attributed the stop to Critic output validation and identified the unreviewed second Proposer message. |

Every first-pass case required a repair for missing both-role references; the capped case also invented an `r6-proposer` reference, which validation rejected. These failures remain visible in the logs.

### Final prompt pass: two targeted improvements, one unresolved failure

| Case | Evidence | Calls | Observed result |
| --- | --- | --- | --- |
| Placeholder contradiction | [Metadata](runs/report-quality-review/placeholder/20261005T031528Z-c475e490/metadata.json), [raw transcript](runs/report-quality-review/placeholder/20261005T031528Z-c475e490/transcript.md) | 1 | Report failed: multiple agreed items cited only the Proposer. No `final.json` was written. The raw response also retained the placeholder contradiction despite the worked example. |
| Capped report | [Final report](runs/report-quality-review/capped/20261005T031528Z-849ce02c/final.json) | 1 | Passed without repair. The affected sixth criterion is now `proposed`, cites r2/r3 exchanges, and explicitly acknowledges rollout exclusions and C2/C5 conditions. Both outstanding blockers are in `unresolved_scope`; outcome remains `capped`. |
| Error explanation | [Final report](runs/report-quality-review/error/20261005T031529Z-0af9ef2d/final.json) | 1 | Passed without repair. The summary attributes the interruption to validation before an accepted second Critic review, without blaming the first-round rule. C1–C3 and the unreviewed responses are retained in `unresolved_scope`; outcome remains `error`. |

The capped and error reports demonstrate improvements on their specific failure cases. They are not comprehensive semantic audits or proof of a higher general success rate. In the placeholder case, the raw response still calls the placeholder agreed and confidentiality-respecting while asking whether it should reveal that a restricted contact exists. It also accepts the assumption that the designation is not secret. The explicit prompt example did not resolve that tension in this attempt.

**Remaining limitation:** the approved changes are implemented, but report consistency is not fully solved. Prompt instructions can be ignored, and valid references do not establish that every claim is supported. No generated report was manually repaired or relabelled to manufacture success. Review material agreements, qualifications, and open questions against their cited messages before using a report as a final specification. No additional model calls, schema changes, termination changes, or extra reviewer agent were introduced after this bounded evaluation.

## Recent manual runs

These five terminal executions supplement the historical samples and frozen-dialogue evaluations above. They were not rerun for this documentation update, and their original inputs, traces, metadata, and available final reports are preserved unchanged. Folder timestamps are UTC. The first four use the right-contact request; the latest uses the engagement-history request.

### Recorded settings and outcomes

All five used `claude-haiku-4-5-20251001`, 8192 maximum output tokens per call, a shared 24-call budget, and one provider retry. The first three allowed four rounds, one output repair, and 250000 input bytes per attempt. The last two allowed eight rounds, two output repairs, and 500000 input bytes per attempt, matching the current defaults.

| Run | Completed rounds | Deliberation | Report | Calls | Evidence |
| --- | --- | --- | --- | --- | --- |
| `20261005T004956Z-65334dc7` | 4 | `stalled` | succeeded | 10 | [Metadata](runs/20261005T004956Z-65334dc7/metadata.json) · [Trace](runs/20261005T004956Z-65334dc7/transcript.md) · [Events](runs/20261005T004956Z-65334dc7/exchanges.jsonl) · [Report](runs/20261005T004956Z-65334dc7/final.json) |
| `20261005T012023Z-d64106fe` | 4 | `completed` | succeeded | 10 | [Metadata](runs/20261005T012023Z-d64106fe/metadata.json) · [Trace](runs/20261005T012023Z-d64106fe/transcript.md) · [Events](runs/20261005T012023Z-d64106fe/exchanges.jsonl) · [Report](runs/20261005T012023Z-d64106fe/final.json) |
| `20261005T021432Z-b7e64989` | 4 | `capped` | failed | 10 | [Metadata](runs/20261005T021432Z-b7e64989/metadata.json) · [Trace](runs/20261005T021432Z-b7e64989/transcript.md) · [Events](runs/20261005T021432Z-b7e64989/exchanges.jsonl); no `final.json`. |
| `20261005T023613Z-9ac1e50b` | 2 | `completed` | succeeded | 7 | [Metadata](runs/20261005T023613Z-9ac1e50b/metadata.json) · [Trace](runs/20261005T023613Z-9ac1e50b/transcript.md) · [Events](runs/20261005T023613Z-9ac1e50b/exchanges.jsonl) · [Report](runs/20261005T023613Z-9ac1e50b/final.json) |
| `20261005T032659Z-164354ee` | 5 | `completed` | succeeded | 15 | [Metadata](runs/20261005T032659Z-164354ee/metadata.json) · [Trace](runs/20261005T032659Z-164354ee/transcript.md) · [Events](runs/20261005T032659Z-164354ee/exchanges.jsonl) · [Report](runs/20261005T032659Z-164354ee/final.json) |

### What these runs demonstrate

- **A live stall is recorded.** In `004956Z`, the last accepted Critic signals `stalled` with C1 and C2 still blocking agreement. The signal takes precedence on the fourth and final allowed round. The Summarizer succeeds after one repair; the report is explicitly partial.
- **Completion can take precedence at the cap.** In `012023Z`, the fourth Critic signals completion with no agreement blockers. The outcome is `completed`, rather than `capped`; the report succeeds after one Summarizer repair.
- **The two failure states remain separate.** In `021432Z`, the Critic still requests another exchange with C2 and C5 outstanding, so deliberation is capped at four rounds. Both Summarizer attempts fail validation, leaving `report_status: failed` and no final report. The failed responses remain inspectable in the trace.
- **An eight-round allowance does not force eight rounds.** The right-contact run `023613Z` completes after two rounds, using one Critic repair and one Summarizer repair. Its previously identified placeholder-policy inconsistency remains documented in the earlier evaluation; successful validation does not resolve that semantic concern.
- **A longer recent discussion also completes before its ceiling.** The engagement-history run `032659Z` completes after five of eight allowed rounds. Its 15 calls comprise ten accepted agent turns, three Critic repair attempts, and two Summarizer attempts. This is the main recent end-to-end example linked from the README.

These executions span different prompts, budgets, and, for the latest run, a different request. They do not isolate the effect of increasing rounds or repair allowance, establish a general success rate, or prove every reported claim is supported. They add observable examples of completion, stalling, capping, and report recovery while retaining the earlier failures and findings.

The five exact manual-run folders and the `termination-prompt-review/` and `report-quality-review/` evidence directories are allowlisted in `.gitignore`. Other run directories remain ignored. Existing sample citations are retained; the newer evidence supplements them.
