theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a b c h k
  have h' := h
  induction h generalizing c
  case refl => exact ⟨_, k, .refl _⟩
  case' par ha hb iha ihb => skip
  all_goals
    cases k
    try exact ⟨_, .refl _, h'⟩
    try exact ⟨_, .refl _, .refl _⟩
  case par.par ha' hb' =>
    obtain ⟨_, ha₁, ha₂⟩ := iha ha' ha
    obtain ⟨_, hb₁, hb₂⟩ := ihb hb' hb
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
  case par.red_I =>
    cases I_irreducible _ ha
    exact ⟨_, .red_I _, hb⟩
  case par.red_K =>
    obtain ⟨_, h, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, .red_K .., h⟩
  case par.red_S =>
    obtain ⟨_, _, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .red_S .., .par (.par hx hb) (.par hy hb)⟩
  case red_I.par hc ha =>
    cases I_irreducible _ hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par ha hc =>
    obtain ⟨_, h, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, h, .red_K ..⟩
  case red_S.par hd hc =>
    obtain ⟨_, _, ha, hb, rfl⟩ := Sab_irreducible _ _ _ hd
    exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S ..⟩
