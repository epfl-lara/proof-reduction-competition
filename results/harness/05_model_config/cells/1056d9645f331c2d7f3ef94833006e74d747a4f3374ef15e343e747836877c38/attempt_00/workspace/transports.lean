theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  all_goals cases h₂
  case par.par a a' b b' ha hb iha ihb a'' b'' ha' hb' =>
    obtain ⟨x, hx, hx'⟩ := iha ha'
    obtain ⟨y, hy, hy'⟩ := ihb hb'
    exact ⟨_, .par hx hy, .par hx' hy'⟩
  case' par.red_I | par.red_K | par.red_S => apply symm
  case par.red_I | red_I.par =>
    cases I_irreducible _ (by assumption)
    exact ⟨_, by assumption, .red_I _⟩
  case par.red_K | red_K.par =>
    obtain ⟨x, hx, e⟩ := Ka_irreducible _ _ (by assumption)
    exact ⟨_, hx, e.symm ▸ .red_K _ _⟩
  case par.red_S | red_S.par =>
    obtain ⟨x, y, hx, hy, e⟩ := Sab_irreducible _ _ _ (by assumption)
    exact ⟨_, .par (.par hx (by assumption)) (.par hy (by assumption)), e.symm ▸ ParallelReduction.red_S x y _⟩
  all_goals (refine ⟨_, .refl _, ?_⟩; constructor <;> assumption)
