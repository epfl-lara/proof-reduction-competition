theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a b c h₁ h₂
  have := h₁
  cases h₁
  · exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case red_I.refl | red_K.refl | red_S.refl | par.refl => exact ⟨_, .refl _, this⟩
  case red_I.red_I | red_K.red_K | red_S.red_S => exact ⟨_, .refl _, .refl _⟩
  case red_I.par hc ha => cases hc; exact ⟨_, ha, .red_I _⟩
  case red_K.par hk _ => obtain ⟨y, hy, rfl⟩ := Ka_irreducible _ _ hk; exact ⟨_, hy, .red_K ..⟩
  case red_S.par hs hc =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ hs
    exact ⟨_, .par (.par hx hc) (.par hy hc), .red_S ..⟩
  case par.red_I hc ha => cases hc; exact ⟨_, .red_I _, ha⟩
  case par.red_K _ hk => obtain ⟨y, hy, rfl⟩ := Ka_irreducible _ _ hk; exact ⟨_, .red_K .., hy⟩
  case par.red_S hc _ _ hs =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ hs
    exact ⟨_, .red_S .., .par (.par hx hc) (.par hy hc)⟩
  case par.par ha hb _ _ ha' hb' =>
    obtain ⟨x, hx, hx'⟩ := parallelReduction_diamond ha ha'
    obtain ⟨y, hy, hy'⟩ := parallelReduction_diamond hb hb'
    exact ⟨_, .par hx hy, .par hx' hy'⟩