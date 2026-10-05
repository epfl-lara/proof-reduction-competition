theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hs : (P : Set (Set S)).Intersecting :=
    fun A hA B hB h => hPP A hA B hB h.inter_eq
  apply Nat.eq_of_mul_eq_mul_left (by decide : 0 < 2)
  rw [mul_pow_sub_one Fintype.card_ne_zero, ← Fintype.card_set]
  apply hs.is_max_iff_card_eq.mp
  intro Q hQ hPQ
  apply Finset.Subset.antisymm hPQ
  intro T hT
  by_contra hn
  exact hPS ⟨T, hn, fun U hU hTU =>
    hQ hT (hPQ hU) (Set.disjoint_iff_inter_eq_empty.mpr hTU)⟩
