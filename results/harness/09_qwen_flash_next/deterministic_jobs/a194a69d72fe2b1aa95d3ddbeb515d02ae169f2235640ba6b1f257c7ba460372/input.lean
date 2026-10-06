theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a b c h₁ h₂
  cases h₁
  · exact ⟨_, h₂, .refl _⟩
  · cases h₂
    · exact ⟨_, .refl _, .red_I _⟩
    · exact ⟨_, .refl _, .refl _⟩
    · next ha hb => exact ⟨_, hb, I_irreducible _ ha ▸ .red_I _⟩
  · cases h₂
    · exact ⟨_, .refl _, .red_K ..⟩
    · exact ⟨_, .refl _, .refl _⟩
    · next ha hb =>
        obtain ⟨u, hu, rfl⟩ := Ka_irreducible _ _ ha
        exact ⟨_, hu, .red_K ..⟩
  · cases h₂
    · exact ⟨_, .refl _, .red_S ..⟩
    · exact ⟨_, .refl _, .refl _⟩
    · next ha hb =>
        obtain ⟨u, v, hu, hv, rfl⟩ := Sab_irreducible _ _ _ ha
        exact ⟨_, .par (.par hu hb) (.par hv hb), .red_S ..⟩
  · next ha hb =>
      cases h₂
      · exact ⟨_, .refl _, .par ha hb⟩
      · exact ⟨_, I_irreducible _ ha ▸ .red_I _, hb⟩
      · obtain ⟨u, hu, rfl⟩ := Ka_irreducible _ _ ha
        exact ⟨_, .red_K .., hu⟩
      · obtain ⟨u, v, hu, hv, rfl⟩ := Sab_irreducible _ _ _ ha
        exact ⟨_, .red_S .., .par (.par hu hb) (.par hv hb)⟩
      · next ha' hb' =>
          obtain ⟨_, x, y⟩ := parallelReduction_diamond ha ha'
          obtain ⟨_, u, v⟩ := parallelReduction_diamond hb hb'
          exact ⟨_, .par x u, .par y v⟩