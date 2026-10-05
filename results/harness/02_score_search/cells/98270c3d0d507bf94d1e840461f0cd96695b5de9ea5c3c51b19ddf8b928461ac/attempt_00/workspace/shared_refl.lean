theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case' par ha hb iha ihb => skip
  all_goals cases h₂ <;> try (refine ⟨_, .refl _, ?_⟩; constructor <;> assumption)
  case red_I.par hc ha =>
    cases I_irreducible _ hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par ha hb =>
    obtain ⟨a', ha', rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, ha', .red_K ..⟩
  case red_S.par hab hc =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ hab
    exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S ..⟩
  case par.red_I =>
    cases I_irreducible _ ha
    exact ⟨_, .red_I _, hb⟩
  case par.red_K =>
    obtain ⟨a', ha', rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, .red_K .., ha'⟩
  case par.red_S =>
    obtain ⟨a', b', ha', hb', rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .red_S .., .par (.par ha' hb) (.par hb' hb)⟩
  case par.par ha' hb' =>
    obtain ⟨a₃, ha₃, ha₃'⟩ := iha ha'
    obtain ⟨b₃, hb₃, hb₃'⟩ := ihb hb'
    exact ⟨_, .par ha₃ hb₃, .par ha₃' hb₃'⟩
