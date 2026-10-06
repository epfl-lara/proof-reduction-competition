# Gemini 3.8 Flash/high: corrected PTY pilot

This pilot uses the same Gemini 3.8 Flash/high condition, frozen standard
Gemini API-equivalent rates, $3 per-problem cost tracking, 3420-second
whole-problem deadline, revised V2 task, cached references and host proof tools
as [the initial protocol](../gemini38_flash_high_3usd/PROTOCOL.md).

The initial `CallElimCorrect.substOldPostSubset` attempt could not use the
native command tool because Landlock denied `/dev/ptmx`. It was interrupted
with a complete native terminal usage record: **$0.28447995 estimated**, zero
host tool checks, incomplete outcome. Its request, result and original budget
remain unchanged in `../gemini38_flash_high_3usd`; that problem is not resampled
or given a new budget here.

The corrected adapter allows `/dev/ptmx` and `/dev/pts`, which the native tool
needs to allocate a PTY and open its slave device. An offline kernel test
verifies PTY allocation while writes to pinned sources and host evidence
remain blocked. Other write permissions and prompt policy are unchanged.
The corrected runtime is a new isolated copy; the initial runtime is preserved.

Run **one pilot theorem**, `CallElimCorrect.extractedOldExprInVars`, with
`--pilot --name CallElimCorrect.extractedOldExprInVars`. This fresh problem has
its own $3 estimate and 57-minute deadline. An audited pilot precedes any
expansion; a partial cohort has no full-cohort mean. Native `init.model` is
selection evidence and does not attest the served backend. In-flight usage
can overshoot the estimated cap; subscription/cache-storage charges remain
unobserved.
