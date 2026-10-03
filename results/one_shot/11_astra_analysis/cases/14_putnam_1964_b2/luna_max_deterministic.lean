theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have h_alt : ∀ A : Set S, A ∉ P → Aᶜ ∈ P := by grind
  have h_not_both : ∀ A : Set S, A ∈ P → Aᶜ ∉ P := by
    intro A hA hAc
    apply hPP A hA Aᶜ hAc
    ext x
    simp
  let Q : Finset (Set S) := (Finset.univ : Finset (Set S)) \ P
  have h_card : P.card = Q.card := by
    exact Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
      (fun A hA => by grind)
      (fun A hA => h_alt A (Finset.mem_sdiff.mp hA).2)
      (by intro A hA; simp)
      (by intro A hA; simp)
  have h_sum : P.card + Q.card = 2 ^ Fintype.card S := by
    have h := Finset.card_sdiff_add_card_eq_card (Finset.subset_univ P)
    change Q.card + P.card = (Finset.univ : Finset (Set S)).card at h
    have hu : (Finset.univ : Finset (Set S)).card = 2 ^ Fintype.card S := by
      simp only [Finset.card_univ, Fintype.card_set]
    rw [hu] at h
    omega
  have hn : Fintype.card S - 1 + 1 = Fintype.card S := by
    have hpos : 0 < Fintype.card S := by positivity
    omega
  have h_pow : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    calc
      2 ^ (Fintype.card S - 1) * 2 = 2 ^ (Fintype.card S - 1) * 2 ^ 1 := rfl
      _ = 2 ^ ((Fintype.card S - 1) + 1) := by rw [← pow_add]
      _ = 2 ^ Fintype.card S := by rw [hn]
  omega
