theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have missing : ∀ A : Set S, A ∉ P → ∃ U ∈ P, A ∩ U = ∅ := by
    intro A hA
    by_contra h
    push_neg at h
    exact hPS ⟨A, hA, fun U hU => (h U hU).ne_empty⟩
  have either : ∀ A : Set S, A ∈ P ∨ Aᶜ ∈ P := by
    intro A
    by_contra! h
    obtain ⟨U, hU, eU⟩ := missing A h.1
    obtain ⟨V, hV, eV⟩ := missing Aᶜ h.2
    apply hPP U hU V hV
    apply Set.eq_empty_of_forall_not_mem
    intro x hx
    by_cases ha : x ∈ A
    · have : x ∈ A ∩ U := ⟨ha, hx.1⟩
      rw [eU] at this
      exact this
    · have : x ∈ Aᶜ ∩ V := ⟨ha, hx.2⟩
      rw [eV] at this
      exact this
  have not_both : ∀ A : Set S, A ∈ P → Aᶜ ∉ P := by
    intro A hA hc
    exact hPP A hA Aᶜ hc (Set.inter_compl_self A)
  let Q : Finset (Set S) := Finset.univ \ P
  have eqcard : P.card = Q.card := by
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    · intro A hA
      exact compl_compl A
    · intro A hA
      exact compl_compl A
    · intro A hA
      simpa [Q] using not_both A hA
    · intro A hA
      exact (either A).resolve_left (by simpa [Q] using hA)
  have total : P.card + Q.card = 2 ^ Fintype.card S := by
    have h := Finset.card_sdiff_add_card_eq_card (Finset.subset_univ P)
    have hc : (Finset.univ : Finset (Set S)).card = 2 ^ Fintype.card S := by
      simp
    change Q.card + P.card = (Finset.univ : Finset (Set S)).card at h
    omega
  have pos : 0 < Fintype.card S := Fintype.card_pos
  have power : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel pos]
  omega
