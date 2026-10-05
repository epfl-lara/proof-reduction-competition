theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  all_goals cases h₂
  case par.par a a' b b' ha' hb' iha ihb a'' b'' ha'' hb'' =>
    obtain ⟨a₃, ha₁, ha₂⟩ := iha ha''
    obtain ⟨b₃, hb₁, hb₂⟩ := ihb hb''
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
  case' red_I.par | red_K.par | red_S.par => apply symm
  case par.red_I a' b b' hb' ihb ha' iha | red_I.par a' b' ha' hb' =>
    cases I_irreducible a' ha'
    exact ⟨_, .red_I _, hb'⟩
  case par.red_K a' b b' hb' ihb ha' iha | red_K.par a' b' ha' hb' =>
    obtain ⟨a₂', ha, rfl⟩ := Ka_irreducible _ a' ha'
    exact ⟨_, .red_K _ _, ha⟩
  case par.red_S a' b b' hb' ihb a c ha' iha | red_S.par a c b a' b' ha' hb' =>
    obtain ⟨a'', c', ha, hc, rfl⟩ := Sab_irreducible a c a' ha'
    exact ⟨_, .red_S _ _ _, .par (.par ha hb') (.par hc hb')⟩
  all_goals (refine ⟨_, .refl _, ?_⟩; constructor <;> assumption)
