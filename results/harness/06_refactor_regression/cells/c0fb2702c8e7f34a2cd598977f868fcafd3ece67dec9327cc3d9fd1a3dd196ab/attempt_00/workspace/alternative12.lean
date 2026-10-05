theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  simp only [ne_eq, ← Set.disjoint_iff_inter_eq_empty] at hPP hPS
  apply Nat.eq_of_mul_eq_mul_left Nat.two_pos
  rw [← pow_succ', Nat.sub_add_cancel (Fintype.card_pos (α := S)),
    ← Fintype.card_set]
  apply (Set.Intersecting.is_max_iff_card_eq hPP).1
  exact fun Q hQ hPQ => hPQ.antisymm fun A hA =>
    not_not.mp fun hn => hPS ⟨A, hn, fun U hU => hQ hA (hPQ hU)⟩
