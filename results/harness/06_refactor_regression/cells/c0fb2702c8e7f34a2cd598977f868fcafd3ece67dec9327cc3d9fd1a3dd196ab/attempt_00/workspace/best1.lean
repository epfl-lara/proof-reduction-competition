theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hm (A : Set S) (hA : ∀ U ∈ P, A ∩ U ≠ ∅) : A ∈ P := by
    by_contra hn
    exact hPS ⟨A, hn, hA⟩
  have hc (A : Set S) : Aᶜ ∈ P ↔ A ∉ P := by
    constructor
    · intro hn hA
      exact hPP A hA Aᶜ hn (Set.inter_compl_self A)
    · intro hn
      apply hm
      intro U hU hAU
      rw [← Set.disjoint_iff_inter_eq_empty, Set.disjoint_compl_left_iff_subset] at hAU
      apply hn
      apply hm
      intro V hV hAV
      exact hPP U hU V hV (Set.disjoint_iff_inter_eq_empty.mp
        (Disjoint.mono_left hAU (Set.disjoint_iff_inter_eq_empty.mpr hAV)))
  have hc' : P.card = Pᶜ.card := by
    apply Finset.card_bijective (compl : Set S → Set S) compl_bijective
    intro A
    simp only [Finset.mem_compl, hc, not_not]
  have hs := Finset.card_add_card_compl P
  rw [← hc', Fintype.card_set] at hs
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel (Fintype.card_pos : 1 ≤ Fintype.card S)]
  omega
