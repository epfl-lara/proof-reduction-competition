theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hI : (P : Set (Set S)).Intersecting :=
    fun A hA B hB h => hPP A hA B hB h.eq_bot
  have hc := hI.is_max_iff_card_eq.mp (by
    intro Q hQ hPQ
    apply Finset.Subset.antisymm hPQ
    intro T hT
    by_contra h
    exact hPS ⟨T, h, fun U hU he =>
      hQ hT (hPQ hU) (Set.disjoint_iff_inter_eq_empty.mpr he)⟩)
  apply Nat.eq_of_mul_eq_mul_left (by decide : 0 < 2)
  rw [hc, Fintype.card_set, ← pow_succ',
    Nat.sub_add_cancel (Fintype.card_pos (α := S))]