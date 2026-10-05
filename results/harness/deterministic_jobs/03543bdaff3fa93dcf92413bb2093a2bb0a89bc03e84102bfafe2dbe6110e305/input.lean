theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hI : (P : Set (Set S)).Intersecting := by
    simpa only [Set.Intersecting, Set.disjoint_iff_inter_eq_empty] using hPP
  have h := hI.is_max_iff_card_eq.mp (by
    intro Q hQ hPQ
    apply Finset.Subset.antisymm hPQ
    intro T hT
    by_contra hT'
    exact hPS ⟨T, hT', fun U hU h =>
      hQ hT (hPQ hU) (Set.disjoint_iff_inter_eq_empty.mpr h)⟩)
  apply Nat.mul_left_cancel (by decide : 0 < 2)
  rw [h, Fintype.card_set, ← pow_succ', Nat.sub_add_cancel Fintype.card_pos]