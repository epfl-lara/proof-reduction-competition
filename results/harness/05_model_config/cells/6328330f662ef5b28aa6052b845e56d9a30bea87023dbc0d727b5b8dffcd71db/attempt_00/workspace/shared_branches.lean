theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case red_I.red_I | red_K.red_K | red_S.red_S => exact ⟨_, .refl _, .refl _⟩
  case red_I.refl | red_K.refl | red_S.refl | par.refl =>
    refine ⟨_, .refl _, ?_⟩
    constructor <;> assumption
  case red_I.par hc ha | par.red_I ha _ hc _ =>
    obtain rfl := I_irreducible _ hc
    first | exact ⟨_, ha, .red_I _⟩ | exact ⟨_, .red_I _, ha⟩
  case red_K.par ha hb | par.red_K hb _ ha _ =>
    obtain ⟨c, h, rfl⟩ := Ka_irreducible _ _ ha
    first | exact ⟨_, h, .red_K _ _⟩ | exact ⟨_, .red_K _ _, h⟩
  case red_S.par hab hc | par.red_S hc _ a b hab _ =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ hab
    first
    | exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S _ _ _⟩
    | exact ⟨_, .red_S _ _ _, .par (.par ha hc) (.par hb hc)⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a, ha₁, ha₂⟩ := iha ha'
    obtain ⟨b, hb₁, hb₂⟩ := ihb hb'
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
