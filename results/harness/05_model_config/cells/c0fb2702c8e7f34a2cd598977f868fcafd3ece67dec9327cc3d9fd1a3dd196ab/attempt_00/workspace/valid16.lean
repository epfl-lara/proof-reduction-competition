theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [ne_eq, ← Set.disjoint_iff_inter_eq_empty] at hPP hPS
  rw [← Nat.mul_right_cancel_iff Nat.two_pos,
    Nat.pow_pred_mul Fintype.card_pos, Nat.mul_comm, ← Fintype.card_set]
  apply (Set.Intersecting.is_max_iff_card_eq hPP).mp
  clear hPP
  grind [Set.Intersecting]
