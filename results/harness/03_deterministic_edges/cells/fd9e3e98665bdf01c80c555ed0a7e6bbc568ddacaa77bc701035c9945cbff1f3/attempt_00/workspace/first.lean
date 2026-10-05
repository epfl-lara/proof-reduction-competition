theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂ with
  | refl => exact ⟨a₂, h₂, .refl _⟩
  | par ha hb iha ihb =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .par ha hb⟩
    | par ha' hb' =>
      obtain ⟨x, hx, hx'⟩ := iha ha'
      obtain ⟨y, hy, hy'⟩ := ihb hb'
      exact ⟨_, .par hx hy, .par hx' hy'⟩
    | red_I =>
      cases I_irreducible _ ha
      exact ⟨_, .red_I _, hb⟩
    | red_K =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, .red_K _ _, hx⟩
    | red_S =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
      exact ⟨_, .red_S _ _ _, .par (.par hx hb) (.par hy hb)⟩
  | red_I a =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_I _⟩
    | red_I => exact ⟨_, .refl _, .refl _⟩
    | par hc ha =>
      cases I_irreducible _ hc
      exact ⟨_, ha, .red_I _⟩
  | red_K a b =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_K _ _⟩
    | red_K => exact ⟨_, .refl _, .refl _⟩
    | par ha hb =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, hx, .red_K _ _⟩
  | red_S a b c =>
    cases h₂ with
    | refl => exact ⟨_, .refl _, .red_S _ _ _⟩
    | red_S => exact ⟨_, .refl _, .refl _⟩
    | par ha hc =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
      exact ⟨_, .par (.par hx hc) (.par hy hc), .red_S _ _ _⟩
