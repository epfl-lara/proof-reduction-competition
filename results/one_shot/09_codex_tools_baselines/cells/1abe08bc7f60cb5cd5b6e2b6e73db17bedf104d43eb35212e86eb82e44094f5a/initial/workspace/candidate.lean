theorem putnam_1964_b2
(S : Type*) [Fintype S] [Nonempty S]
(P : Finset (Set S))
(hPP : ∀ T ∈ P, ∀ U ∈ P, T ∩ U ≠ ∅)
(hPS : ¬∃ T : Set S, T ∉ P ∧ (∀ U ∈ P, T ∩ U ≠ ∅))
: (P.card = 2 ^ (Fintype.card S - 1)) := by
  classical
  have witness (A : Set S) (hA : A ∉ P) : ∃ U ∈ P, A ∩ U = ∅ := by
    by_contra hn
    apply hPS
    refine ⟨A, hA, ?_⟩
    intro U hU
    intro he
    exact hn ⟨U, hU, he⟩
  have cover (A : Set S) : A ∈ P ∨ Aᶜ ∈ P := by
    by_contra hn
    have hA : A ∉ P := by aesop
    have hAc : Aᶜ ∉ P := by aesop
    obtain ⟨U, hU, hAU⟩ := witness A hA
    obtain ⟨V, hV, hAV⟩ := witness Aᶜ hAc
    have hdis : U ∩ V = ∅ := by
      ext x
      simp only [Set.mem_inter_iff, Set.mem_empty_iff_false, iff_false, not_and]
      intro hxU hxV
      have hxA : x ∉ A := by
        intro hx
        have : x ∈ A ∩ U := ⟨hx, hxU⟩
        rw [hAU] at this
        exact this
      have hxAc : x ∈ Aᶜ := by simpa using hxA
      have : x ∈ Aᶜ ∩ V := ⟨hxAc, hxV⟩
      rw [hAV] at this
      exact this
    exact hPP U hU V hV (by simpa [hdis])
  have noBoth (A : Set S) (hA : A ∈ P) : Aᶜ ∉ P := by
    intro h
    have := hPP A hA Aᶜ h
    simpa using this
  let Q : Finset (Set S) := Finset.univ \ P
  have hcard : P.card = Q.card := by
    have himage : Q = P.image (fun A : Set S => Aᶜ) := by
      ext A
      simp only [Q, Finset.mem_sdiff, Finset.mem_univ, true_and,
        Finset.mem_image]
      constructor
      · intro hA
        obtain h | h := cover Aᶜ
        · exact ⟨Aᶜ, h, by simp⟩
        · exact False.elim (hA (by simpa using h))
      · rintro ⟨B, hB, rfl⟩
        exact noBoth B hB
    rw [himage]
    exact (Finset.card_image_iff.mpr (by
      intro A hA B hB h
      simpa using congrArg (fun X : Set S => Xᶜ) h)).symm
  have htotal : P.card + Q.card = 2 ^ Fintype.card S := by
    have hdis : Disjoint P Q := Finset.disjoint_left.mpr (by
      intro A hA hAQ
      exact (Finset.mem_sdiff.mp hAQ).2 hA)
    have hunion : P ∪ Q = Finset.univ := by
      ext A
      simp only [Finset.mem_union, Finset.mem_sdiff, Finset.mem_univ, true_and]
      constructor
      · intro _; trivial
      · intro _
        obtain h | h := cover A
        · exact Or.inl h
        · right
          refine ⟨trivial, ?_⟩
          intro hA
          exact noBoth A hA (by simpa using h)
    rw [← Finset.card_union_of_disjoint hdis, hunion]
    simp [Fintype.card_fun]
  have hdouble : P.card * 2 = 2 ^ Fintype.card S := by omega
  have hn : 0 < Fintype.card S := Fintype.card_pos
  have hpow : 2 ^ (Fintype.card S - 1) * 2 = 2 ^ Fintype.card S := by
    rw [← pow_succ, Nat.sub_add_cancel (by omega)]
  omega
