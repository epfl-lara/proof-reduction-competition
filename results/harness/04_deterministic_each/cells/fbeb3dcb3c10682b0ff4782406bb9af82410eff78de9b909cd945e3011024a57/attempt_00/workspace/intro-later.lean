theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁
  induction h₁ generalizing a₂ <;> intro h₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case' par.red_I | par.red_K | par.red_S => apply symm
  case red_I.par | par.red_I =>
    cases I_irreducible _ ‹_›
    exact ⟨_, ‹_›, .red_I _⟩
  case red_K.par | par.red_K =>
    obtain ⟨a', h, rfl⟩ := Ka_irreducible _ _ ‹_›
    exact ⟨_, h, .red_K ..⟩
  case red_S.par | par.red_S =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ ‹_›
    exact ⟨_, .par (.par ha ‹_›) (.par hb ‹_›), .red_S ..⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a', h, h'⟩ := iha ha'
    obtain ⟨b', k, k'⟩ := ihb hb'
    exact ⟨_, .par h k, .par h' k'⟩
  all_goals refine ⟨_, .refl _, ?_⟩ <;> constructor <;> assumption
