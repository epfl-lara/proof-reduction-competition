theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  have hc : ∀ A : Set S, A ∈ P ∨ Aᶜ ∈ P := by grind
  have hn : ∀ A : Set S, A ∈ P → Aᶜ ∉ P := by
    intro A hA h
    have := hPP A hA Aᶜ h
    simpa using this
  classical
  let Q : Finset (Set S) := Finset.univ \ P
  have heq : P.card = Q.card := by
    have h₁ : ∀ A : Set S, A ∈ P → Aᶜ ∈ Q := by
      intro A hA
      have h := hc A
      simp [Q, hn A hA] at *
      rcases h with hp | hp
      · exact False.elim (hn A hA hp)
      · simpa [Q] using hp
    have h₂ : ∀ A : Set S, A ∈ Q → Aᶜ ∈ P := by
      intro A hA
      have h := hc Aᶜ
      simp [Q] at hA
      rcases h with hp | hp
      · simpa using hp
      · exact False.elim (hA hp)
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    <;> simp_all
  have hsum : P.card + Q.card = 2 ^ Fintype.card S := by
    have : P.card + Q.card = (Finset.univ : Finset (Set S)).card := by grind
    rw [this]
    simp only [Finset.card_univ, Fintype.card_set]
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    have h : Fintype.card S - 1 + 1 = Fintype.card S := by omega
    rw [show 2 = 2 ^ (1 : ℕ) by rfl, ← pow_add, h]
  omega
