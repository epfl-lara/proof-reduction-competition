theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂ with
  | refl => exact ⟨_, h₂, .refl _⟩
  | par ha hb iha ihb =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .par ha hb⟩
    | par ha' hb' =>
      obtain ⟨a, ha₁, ha₂⟩ := iha ha'
      obtain ⟨b, hb₁, hb₂⟩ := ihb hb'
      exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
    | red_I =>
      cases I_irreducible _ ha
      exact ⟨_, .red_I _, hb⟩
    | red_K =>
      obtain ⟨a, h, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, .red_K .., h⟩
    | red_S =>
      obtain ⟨a, b, hx, hb', rfl⟩ := Sab_irreducible _ _ _ ha
      exact ⟨_, .red_S .., .par (.par hx hb) (.par hb' hb)⟩
  | red_I =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_I _⟩
    | red_I => exact ⟨_, .refl _, .refl _⟩
    | par hc ha =>
      cases I_irreducible _ hc
      exact ⟨_, ha, .red_I _⟩
  | red_K =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_K ..⟩
    | red_K => exact ⟨_, .refl _, .refl _⟩
    | par ha hc =>
      obtain ⟨a, h, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, h, .red_K ..⟩
  | red_S =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_S ..⟩
    | red_S => exact ⟨_, .refl _, .refl _⟩
    | par hd hc =>
      obtain ⟨a, b, ha, hb, rfl⟩ := Sab_irreducible _ _ _ hd
      exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S ..⟩
