theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case' red_I.par | par.red_I =>
    obtain rfl := I_irreducible _ (by assumption)
  case' red_K.par | par.red_K =>
    obtain ⟨a', h, rfl⟩ := Ka_irreducible _ _ (by assumption)
  case' red_S.par | par.red_S =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ (by assumption)
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a', h, h'⟩ := iha ha'
    obtain ⟨b', k, k'⟩ := ihb hb'
    exact ⟨_, .par h k, .par h' k'⟩
  all_goals
    solve_by_elim (maxDepth := 12) [Exists.intro, And.intro, ParallelReduction.par,
      ParallelReduction.red_I, ParallelReduction.red_K, ParallelReduction.red_S,
      ParallelReduction.refl]