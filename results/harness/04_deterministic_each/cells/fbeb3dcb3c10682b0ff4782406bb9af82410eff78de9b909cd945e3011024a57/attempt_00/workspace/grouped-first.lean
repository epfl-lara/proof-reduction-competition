theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  all_goals try (refine ⟨_, .refl _, ?_⟩; constructor <;> assumption)
  case red_I.par | par.red_I =>
    obtain rfl := I_irreducible _ (by assumption)
    first | exact ⟨_, .red_I _, by assumption⟩ | exact ⟨_, by assumption, .red_I _⟩
  case red_K.par | par.red_K =>
    obtain ⟨a', h, rfl⟩ := Ka_irreducible _ _ (by assumption)
    first | exact ⟨_, .red_K .., h⟩ | exact ⟨_, h, .red_K ..⟩
  case red_S.par | par.red_S =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ (by assumption)
    first
    | exact ⟨_, .red_S .., .par (.par ha (by assumption)) (.par hb (by assumption))⟩
    | exact ⟨_, .par (.par ha (by assumption)) (.par hb (by assumption)), .red_S ..⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a', h, h'⟩ := iha ha'
    obtain ⟨b', k, k'⟩ := ihb hb'
    exact ⟨_, .par h k, .par h' k'⟩
