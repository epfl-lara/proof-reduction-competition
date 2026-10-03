theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have hc : ∀ A : Set S, A ∈ P ∨ Aᶜ ∈ P := by grind
  have hn : ∀ A : Set S, A ∈ P → Aᶜ ∉ P := by
    intro A hA hAc
    have : A ∩ Aᶜ = ∅ := by simp
    simpa [this] using hPP A hA Aᶜ hAc
  let Q := (Finset.univ : Finset (Set S)) \ P
  have hcard : P.card = Q.card := by
    
    have h2 : ∀ A : Set S, A ∈ Q → Aᶜ ∈ P := by grind
    apply Finset.card_bij' (fun A _ => Aᶜ) (fun A _ => Aᶜ)
    <;> simp_all [Q]
  have hsum : P.card + Q.card = 2 ^ Fintype.card S := by
    have h : P.card + Q.card = (Finset.univ : Finset (Set S)).card := by grind
    rw [h]
    simp only [Finset.card_univ, Fintype.card_set]
  have hpos : 0 < Fintype.card S := by positivity
  have hp : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ]
    congr 1
    omega
  omega
