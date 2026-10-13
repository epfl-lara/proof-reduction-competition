theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case' red_I.par | red_K.par | red_S.par => apply _root_.symm
  case red_I.par | par.red_I =>
    obtain rfl := I_irreducible _ ‹_›
    exact ⟨_, .red_I _, ‹_›⟩
  case red_K.par | par.red_K =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ‹_›
    exact ⟨_, .red_K .., hx⟩
  case red_S.par | par.red_S =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ‹_›
    exact ⟨_, .red_S .., by apply ParallelReduction.par <;> apply ParallelReduction.par <;> assumption⟩
  case par.par iha ihb e f ha' hb' =>
    obtain ⟨x, hx⟩ := iha ha'
    obtain ⟨y, hy⟩ := ihb hb'
    exact ⟨_, .par hx.1 hy.1, .par hx.2 hy.2⟩
  repeat' constructor
  all_goals assumption