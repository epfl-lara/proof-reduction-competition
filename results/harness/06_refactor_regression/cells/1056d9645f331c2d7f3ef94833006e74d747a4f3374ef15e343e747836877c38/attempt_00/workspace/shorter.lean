theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  all_goals cases h₂
  case par.par iha ihb a'' b'' ha'' hb'' =>
    obtain ⟨a₃, ha₁, ha₂⟩ := iha ha''
    obtain ⟨b₃, hb₁, hb₂⟩ := ihb hb''
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
  case' red_I.par | red_K.par | red_S.par => apply symm
  case par.red_I hb' ihb ha' iha | red_I.par ha' hb' =>
    cases I_irreducible _ ha'
    exact ⟨_, .red_I _, hb'⟩
  case par.red_K ha' iha | red_K.par ha' hb' =>
    obtain ⟨a₂', ha, rfl⟩ := Ka_irreducible _ _ ha'
    exact ⟨_, .red_K .., ha⟩
  case par.red_S hb' ihb a c ha' iha | red_S.par ha' hb' =>
    obtain ⟨a'', c', ha, hc, rfl⟩ := Sab_irreducible _ _ _ ha'
    exact ⟨_, .red_S .., .par (.par ha hb') (.par hc hb')⟩
  all_goals exact ⟨_, .refl _, by constructor <;> assumption⟩
