theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case par a a' b b' ha hb iha ihb =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par a'' b'' ha' hb' =>
      obtain ⟨c, hc, hc'⟩ := iha ha'
      obtain ⟨d, hd, hd'⟩ := ihb hb'
      exact ⟨_, .par hc hd, .par hc' hd'⟩
    case red_I =>
      rw [I_irreducible a' ha]
      exact ⟨_, .red_I _, hb⟩
    case red_K =>
      obtain ⟨c, hc, rfl⟩ := Ka_irreducible a₂ a' ha
      exact ⟨_, .red_K _ _, hc⟩
    case red_S c d =>
      obtain ⟨c', d', hc, hd, rfl⟩ := Sab_irreducible c d a' ha
      exact ⟨_, .red_S _ _ _, .par (.par hc hb) (.par hd hb)⟩
  case red_I =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_I _⟩
    case par c d hc hd =>
      rw [I_irreducible c hc]
      exact ⟨_, hd, .red_I _⟩
    case red_I => exact ⟨_, .refl _, .refl _⟩
  case red_K c =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_K _ _⟩
    case par d e hd he =>
      obtain ⟨d', hd', rfl⟩ := Ka_irreducible _ d hd
      exact ⟨_, hd', .red_K _ _⟩
    case red_K => exact ⟨_, .refl _, .refl _⟩
  case red_S a b c =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_S _ _ _⟩
    case par d e hd he =>
      obtain ⟨a', b', ha, hb, rfl⟩ := Sab_irreducible a b d hd
      exact ⟨_, .par (.par ha he) (.par hb he), .red_S _ _ _⟩
    case red_S => exact ⟨_, .refl _, .refl _⟩
