theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  all_goals cases h₂
  case' par.red_I | par.red_K | par.red_S => apply symm
  case red_I.par hc ha | par.red_I ha _ hc _ =>
    obtain rfl := I_irreducible _ hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par ha hb | par.red_K hb _ ha _ =>
    obtain ⟨c, h, rfl⟩ := Ka_irreducible _ _ ha
    exact ⟨_, h, .red_K _ _⟩
  case red_S.par hab hc | par.red_S hc _ a b hab _ =>
    obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible _ _ _ hab
    exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S _ _ _⟩
  case par.par ha hb iha ihb a' b' ha' hb' =>
    obtain ⟨a, ha₁, ha₂⟩ := iha ha'
    obtain ⟨b, hb₁, hb₂⟩ := ihb hb'
    exact ⟨_, .par ha₁ hb₁, .par ha₂ hb₂⟩
  all_goals
    refine ⟨_, .refl _, ?_⟩
    constructor <;> assumption