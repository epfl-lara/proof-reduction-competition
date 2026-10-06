theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  have h2 := (Set.Intersecting.is_max_iff_card_eq fun a ha b hb =>
      hPP a ha b hb ∘ Disjoint.inter_eq).mp fun t ht hP =>
      hP.antisymm fun x hx => Classical.byContradiction
        (hPS ⟨x, ·, fun U hU => ht hx (hP hU) ∘ Set.disjoint_iff_inter_eq_empty.mpr⟩)
  rw [Fintype.card_set, ← pow_sub_one_mul Fintype.card_ne_zero] at h2
  omega