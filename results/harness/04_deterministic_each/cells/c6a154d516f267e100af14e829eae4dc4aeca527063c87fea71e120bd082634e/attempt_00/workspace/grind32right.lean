theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [← Set.disjoint_iff_inter_eq_empty.not] at hPP hPS
  apply Nat.mul_right_cancel Nat.two_pos
  rw [Nat.pow_pred_mul Fintype.card_pos, Nat.mul_comm P.card, ← Fintype.card_set,
    ← Set.Intersecting.is_max_iff_card_eq hPP]
  grind [Set.Intersecting]
