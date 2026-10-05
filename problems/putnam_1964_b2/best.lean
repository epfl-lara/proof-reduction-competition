-- Warm-up problem: putnam_1964_b2
-- Variant: best; primary Lean version: v4.25.0
-- Target starts at the TARGET DECLARATION marker below.
-- Source context: benchmark header
-- Proof provenance and scores: ../manifest.json

import Mathlib
import Aesop

-- Match the local evaluator elaboration settings; no heartbeat measurement here.
set_option maxHeartbeats 0
set_option Elab.async false

set_option maxHeartbeats 0

open Set Function Filter Topology



-- TARGET DECLARATION BEGIN: putnam_1964_b2
theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [← Set.disjoint_iff_inter_eq_empty.not] at *
  apply Nat.mul_left_cancel Nat.two_pos
  rw [mul_pow_sub_one Fintype.card_ne_zero, ← Fintype.card_set,
    ← Set.Intersecting.is_max_iff_card_eq hPP]
  grind [Set.Intersecting]

-- TARGET DECLARATION END: putnam_1964_b2
