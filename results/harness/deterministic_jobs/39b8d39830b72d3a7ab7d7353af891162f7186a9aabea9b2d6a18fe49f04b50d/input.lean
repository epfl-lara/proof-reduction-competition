theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case' par.red_I | par.red_K | par.red_S => apply symm
  case red_I.par | par.red_I =>
    obtain rfl := I_irreducible _ (by assumption)
    exact ⟨_, by assumption, .red_I _⟩
  case red_K.par | par.red_K =>
    obtain ⟨a', h, e⟩ := Ka_irreducible _ _ (by assumption)
    rw [e]
    exact ⟨_, h, .red_K ..⟩
  case red_S.par | par.red_S =>
    obtain ⟨a', b', ha, hb, e⟩ := Sab_irreducible _ _ _ (by assumption)
    rw [e]
    exact ⟨_, .par (.par ha (by assumption)) (.par hb (by assumption)), .red_S ..⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a', h, h'⟩ := iha ha'
    obtain ⟨b', k, k'⟩ := ihb hb'
    exact ⟨_, .par h k, .par h' k'⟩
  all_goals exact ⟨_, .refl _, by constructor <;> assumption⟩