theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁
  revert a₂
  refine ParallelReduction.rec
    (motive := fun a b _ => ∀ {c}, a ⭢ₚ c → Join ParallelReduction b c)
    ?refl ?red_I ?red_K ?red_S ?par h₁
  case refl => intro a c h; exact ⟨c, h, .refl _⟩
  case' red_I => intro a a₂ h₂; cases h₂
  case' red_K => intro a b a₂ h₂; cases h₂
  case' red_S => intro a b c a₂ h₂; cases h₂
  case' par => intro a a' b b' ha hb iha ihb a₂ h₂; cases h₂
  case par.par iha ihb _ _ ha' hb' =>
    obtain ⟨x, hx, hx'⟩ := iha ha'
    obtain ⟨y, hy, hy'⟩ := ihb hb'
    exact ⟨_, .par hx hy, .par hx' hy'⟩
  case' par.red_I | par.red_K | par.red_S => apply symm
  case par.red_I | red_I.par =>
    cases I_irreducible _ (by assumption)
    exact ⟨_, by assumption, .red_I _⟩
  case par.red_K | red_K.par =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ (by assumption)
    exact ⟨_, hx, .red_K _ _⟩
  case par.red_S | red_S.par =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ (by assumption)
    exact ⟨_, .par (.par hx (by assumption)) (.par hy (by assumption)), .red_S _ _ _⟩
  all_goals (refine ⟨_, .refl _, ?_⟩; constructor <;> assumption)
