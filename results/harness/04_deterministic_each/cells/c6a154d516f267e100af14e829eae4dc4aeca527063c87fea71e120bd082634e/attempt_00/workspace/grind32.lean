theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [← Set.disjoint_iff_inter_eq_empty.not] at hPP hPS
  apply Nat.mul_left_cancel Nat.two_pos
  rw [← pow_succ', Nat.sub_add_cancel Fintype.card_pos, ← Fintype.card_set,
    ← Set.Intersecting.is_max_iff_card_eq hPP]
  grind [Set.Intersecting]
