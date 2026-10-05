theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case red_I.red_I | red_K.red_K | red_S.red_S => exact ⟨_, .refl _, .refl _⟩
  case red_I.refl | red_K.refl | red_S.refl | par.refl =>
    refine ⟨_, .refl _, ?_⟩
    constructor <;> assumption
  case red_I.par hc ha =>
    obtain rfl := I_irreducible _ hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par ha hb =>
    obtain ⟨c, h, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, h, .red_K _ _⟩
  case red_S.par hab hc =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ hab
    exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S _ _ _⟩
  case par.red_I hb ihb ha iha =>
    obtain rfl := I_irreducible _ ha
    exact ⟨_, .red_I _, hb⟩
  case par.red_K hb ihb ha iha =>
    obtain ⟨c, h, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, .red_K _ _, h⟩
  case par.red_S hb ihb a b ha iha =>
    obtain ⟨a', b', ha', hb', rfl⟩ := Sab_irreducible _ _ _ ha
    exact ⟨_, .red_S _ _ _, .par (.par ha' hb) (.par hb' hb)⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a, ha₁, ha₂⟩ := iha ha'
    obtain ⟨b, hb₁, hb₂⟩ := ihb hb'
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
