theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case' par ha hb iha ihb => skip
  all_goals cases h₂
  case' par.red_I | par.red_K | par.red_S => apply symm
  case red_I.par ha hb | par.red_I =>
    cases ha
    exact ⟨_, hb, .red_I _⟩
  case red_K.par ha hb | par.red_K =>
    obtain ⟨a', ha', rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, ha', .red_K ..⟩
  case red_S.par ha hb | par.red_S =>
    obtain ⟨a', b', ha', hb', rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .par (.par ha' hb) (.par hb' hb), .red_S ..⟩
  case par.par ha' hb' =>
    obtain ⟨a₃, ha₃, ha₃'⟩ := iha ha'
    obtain ⟨b₃, hb₃, hb₃'⟩ := ihb hb'
    exact ⟨_, .par ha₃ hb₃, .par ha₃' hb₃'⟩
  all_goals
    refine ⟨_, .refl _, ?_⟩
    constructor <;> assumption
