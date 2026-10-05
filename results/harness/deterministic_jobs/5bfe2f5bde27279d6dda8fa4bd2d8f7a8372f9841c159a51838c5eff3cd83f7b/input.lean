theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  all_goals cases h₂
  case par.par iha ihb _ _ ha' hb' =>
    obtain ⟨x, hx, hx'⟩ := iha ha'
    obtain ⟨y, hy, hy'⟩ := ihb hb'
    exact ⟨_, .par hx hy, .par hx' hy'⟩
  case' par.red_I | par.red_K | par.red_S => apply symm
  case par.red_I | red_I.par =>
    cases I_irreducible _ (by assumption)
    exact ⟨_, by assumption, .red_I _⟩
  case par.red_K | red_K.par =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ (by assumption)
    exact ⟨_, hx, .red_K ..⟩
  case par.red_S hb _ _ _ _ _ | red_S.par hb =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ (by assumption)
    exact ⟨_, .par (.par hx hb) (.par hy hb), .red_S ..⟩
  all_goals exact ⟨_, .refl _, by constructor <;> assumption⟩