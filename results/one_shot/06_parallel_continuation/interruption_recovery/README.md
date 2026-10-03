# Recovery after external interruption

All previous worker processes disappeared when the parent turn was interrupted.
The recovery script verified their absence and acquired all five local admission
locks before changing state. [receipt.json](receipt.json) retains the evidence.

The continuation had **33 new admitted/released HTTP calls and 33 saved new
responses with round results**. Four remaining requests were queued but never
admitted. Each request-start marker matched exactly one unsent admission ticket
within a millisecond. Only those four markers were archived and reset so the
originally planned calls could proceed. No sent request was repeated. Existing
terminal cells and historical reused rounds were left untouched.

The original repair and combined runner implementations and settings remain
frozen; cleanup resumes its checkpoints. Launches use detached processes with
durable output. New RCP workers explicitly load the repository `.env` after
removing inherited `RCP_*` variables. The parent shell held a different key that
would otherwise override the file. Historical processes no longer exist, so
their credential source cannot be verified. No credential values are recorded.

Admission event logs retain their interrupted tails; no synthetic release events
were inserted. The high-effort Qwen3.8 run has two unknown admitted calls and is
closed separately. A combined historical admission audit must account for this
external-stop evidence; an open log tail is not a new live process.
