theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case par a a' b b' ha hb iha ihb =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par a'' b'' ha' hb' =>
      obtain ⟨a₃, ha₃, ha₃'⟩ := iha ha'
      obtain ⟨b₃, hb₃, hb₃'⟩ := ihb hb'
      exact ⟨_, .par ha₃ hb₃, .par ha₃' hb₃'⟩
    case red_I =>
      cases I_irreducible a' ha
      exact ⟨_, .red_I _, hb⟩
    case red_K =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible a₂ a' ha
      exact ⟨_, .red_K _ _, hx⟩
    case red_S a c =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible a c a' ha
      exact ⟨_, .red_S _ _ _, .par (.par hx hb) (.par hy hb)⟩
  case red_I =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_I _⟩
    case par c a' hc ha =>
      cases I_irreducible c hc
      exact ⟨_, ha, .red_I _⟩
    case red_I => exact ⟨_, .refl _, .refl _⟩
  case red_K c =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_K _ _⟩
    case par a' c' ha hc =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ a' ha
      exact ⟨_, hx, .red_K _ _⟩
    case red_K => exact ⟨_, .refl _, .refl _⟩
  case red_S a b c =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_S _ _ _⟩
    case par d c' hd hc =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible a b d hd
      exact ⟨_, .par (.par hx hc) (.par hy hc), .red_S _ _ _⟩
    case red_S => exact ⟨_, .refl _, .refl _⟩
