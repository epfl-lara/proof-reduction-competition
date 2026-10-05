theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂ with
  | refl => exact ⟨_, h₂, .refl _⟩
  | red_I a =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_I _⟩
    | red_I => exact ⟨_, .refl _, .refl _⟩
    | par hc ha =>
      cases I_irreducible _ hc
      exact ⟨_, ha, .red_I _⟩
  | red_K a b =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_K ..⟩
    | red_K => exact ⟨_, .refl _, .refl _⟩
    | par ha hb =>
      obtain ⟨a', h, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, h, .red_K ..⟩
  | red_S a b c =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_S ..⟩
    | red_S => exact ⟨_, .refl _, .refl _⟩
    | par hd hc =>
      obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ hd
      exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S ..⟩
  | par ha hb iha ihb =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .par ha hb⟩
    | red_I =>
      cases I_irreducible _ ha
      exact ⟨_, .red_I _, hb⟩
    | red_K =>
      obtain ⟨a', h, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, .red_K .., h⟩
    | red_S =>
      obtain ⟨a', b', h, h', rfl⟩ := Sab_irreducible _ _ _ ha
      exact ⟨_, .red_S .., .par (.par h hb) (.par h' hb)⟩
    | par ha' hb' =>
      obtain ⟨a', h, h'⟩ := iha ha'
      obtain ⟨b', k, k'⟩ := ihb hb'
      exact ⟨_, .par h k, .par h' k'⟩
