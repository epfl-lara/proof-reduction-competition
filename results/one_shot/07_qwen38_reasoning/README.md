# Separate Qwen3.8 effort probe

**User steering:** ignore Qwen3.8 for now. No further probes or cohorts are
scheduled; preserve the completed medium probe and stopped high cohort as evidence.

**Finished:** medium effort returned no final proof, with `finish_reason=length`.
All **32,768 completion tokens were reported as reasoning**. No candidate reached
Lean evaluation, no repair was attempted, and the incumbent stayed selected.
The cached-reference guard passed. See [summary.json](summary.json) for queue
time separately from the admitted HTTP interval. This does not establish that
all lower-effort settings fail; it does rule out useful delivery in this one
medium-effort request with the repository credential explicitly selected.

One saved plain request on `CallElimCorrect.substOldPostSubset` changes to medium
effort, as requested. Prompt, context, temperature 0.3 and 32,768-token cap stay
fixed. High maps to provider `xhigh`; medium maps to `medium` in the unchanged
client. This is one engineering comparison against a historical response, not a
full benchmark. No repeats, repairs or cleanup are added.

The launch explicitly loads the repository `.env`, removing inherited `RCP_*`
overrides. The parent shell had a different inherited RCP key. Historical workers
no longer exist, so their effective key cannot be verified; this is a possible
transport difference from the historical comparator. No key values are saved.
The shared gate enforces admission; elapsed time includes queuing.

See [launch](launch.json), [log](execution.log), and [artifacts](medium_plain_first/).
The high cohort remains partial, including two admitted calls with unknown
responses/usage that are never repeated. Final probe results separate delivery,
all-version validity, changed proof and score acceptance.
