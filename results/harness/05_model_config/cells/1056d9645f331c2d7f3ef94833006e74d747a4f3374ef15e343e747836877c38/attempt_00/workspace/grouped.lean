theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case par a a' b b' ha hb iha ihb =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par a'' b'' ha' hb' =>
      obtain ⟨x, hx, hx'⟩ := iha ha'
      obtain ⟨y, hy, hy'⟩ := ihb hb'
      exact ⟨_, .par hx hy, .par hx' hy'⟩
    case red_I =>
      cases I_irreducible a' ha
      exact ⟨_, .red_I _, hb⟩
    case red_K =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ a' ha
      exact ⟨_, .red_K _ _, hx⟩
    case red_S =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ a' ha
      exact ⟨_, .red_S _ _ _, .par (.par hx hb) (.par hy hb)⟩
  all_goals cases h₂ <;> try (refine ⟨_, .refl _, ?_⟩; constructor; done)
  case red_I.par c a' hc ha =>
    cases I_irreducible c hc
    exact ⟨_, ha, .red_I _⟩
  case red_K.par a' c' ha hc =>
    obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ a' ha
    exact ⟨_, hx, .red_K _ _⟩
  case red_S.par d c' hd hc =>
    obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ d hd
    exact ⟨_, .par (.par hx hc) (.par hy hc), .red_S _ _ _⟩
