theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a b c h k
  induction h generalizing c
  case refl => exact ⟨_, k, .refl _⟩
  case' par ha hb iha ihb => skip
  all_goals
    cases k
    exact ⟨_, .refl _, by constructor <;> assumption⟩
    try exact ⟨_, .refl _, .refl _⟩
  case par.par ha' hb' =>
    obtain ⟨_, ha₁, ha₂⟩ := iha ha'
    obtain ⟨_, hb₁, hb₂⟩ := ihb hb'
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
  case' par.red_I | par.red_K | par.red_S => apply symm
  case red_I.par | par.red_I =>
    cases I_irreducible _ (by assumption)
    exact ⟨_, by assumption, .red_I _⟩
  case red_K.par | par.red_K =>
    obtain ⟨_, h, rfl⟩ := Ka_irreducible _ _ (by assumption)
    exact ⟨_, h, .red_K ..⟩
  case red_S.par | par.red_S =>
    obtain ⟨_, _, hx, hy, rfl⟩ := Sab_irreducible _ _ _ (by assumption)
    exact ⟨_, .par (.par hx (by assumption)) (.par hy (by assumption)), .red_S ..⟩
