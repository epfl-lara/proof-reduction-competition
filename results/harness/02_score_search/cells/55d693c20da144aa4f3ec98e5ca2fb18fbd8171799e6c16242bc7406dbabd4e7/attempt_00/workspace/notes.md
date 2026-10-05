1. Fin 4 → Icc B T finite-state collision; strong induction with explicit predecessor helper. Valid all versions. 301 tokens, 3313.565 heartbeats; score 93.54547.
2. Replaced four predecessor rewrites/helper by simp (disch := omega) only [Nat.add_sub_assoc, ih]. Valid all versions. 205 tokens, 3716.805 heartbeats; score 95.25914.
3–5. Tried finite interval of Fin 4 → ℤ directly rather than Fin 4 → Icc B T. Anonymous membership constructor needs a tactic proof to defer elaboration. Repaired candidate valid but 217 tokens, 3716.254 heartbeats, score 95.03316 (worse).
6. Inline finite-state map, parameterize h, combine recurrence rewrites with simp. Valid all versions. 196 tokens, 3736.697 heartbeats; score 95.42403.
7. Explicit congrFun/Subtype.val projection and convert ... using 2. Valid all versions. 188 tokens, 3745.324 heartbeats; score 95.57274.
8. Term-style strong induction plus clearing irrelevant facts inside simp discharger: 190 tokens, 3574.484 heartbeats, score 95.57541. Valid, but not accepted as best (tiny delta).
9. Term-style induction, without clearing. Valid all versions. 184 tokens, 3754.856 heartbeats; score 95.64586.
10. Retried direct function interval using forall_and for bounds. Valid all versions, 195 tokens, 3744.164 heartbeats; score 95.44111 (worse). The finite subtype map remains shorter. Remaining alternative inductions require more index arithmetic; stop locally with attempt 9.
