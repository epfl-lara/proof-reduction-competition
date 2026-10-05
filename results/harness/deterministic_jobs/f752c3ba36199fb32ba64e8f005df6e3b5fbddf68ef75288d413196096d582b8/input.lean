theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case par.par iha ihb _ _ ha' hb' =>
    obtain ⟨x, hx, hx'⟩ := iha ha'
    obtain ⟨y, hy, hy'⟩ := ihb hb'
    exact ⟨_, .par hx hy, .par hx' hy'⟩
  case par.red_I hb ihb ha iha =>
    cases I_irreducible _ ha
    exact ⟨_, .red_I _, hb⟩
  case par.red_K hb ihb _ ha iha =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, .red_K .., hx⟩
  case par.red_S hb ihb _ _ ha iha =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .red_S .., .par (.par hx hb) (.par hy hb)⟩
  case red_I.par hc ha =>
    cases I_irreducible _ hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par ha hb =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, hx, .red_K ..⟩
  case red_S.par ha hc =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .par (.par hx hc) (.par hy hc), .red_S ..⟩
  all_goals refine ⟨_, .refl _, ?_⟩; constructor <;> assumption