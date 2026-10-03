theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  cases h₁
  case refl => exact ⟨a₂, h₂, .refl _⟩
  case par a a' b b' ha hb =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par a'' b'' ha' hb' =>
      obtain ⟨x, hx⟩ := parallelReduction_diamond ha ha'
      obtain ⟨y, hy⟩ := parallelReduction_diamond hb hb'
      exact ⟨x ⬝ y, .par hx.1 hy.1, .par hx.2 hy.2⟩
    case red_I =>
      rw [I_irreducible a' ha]
      exact ⟨b', .red_I b', hb⟩
    case red_K =>
      obtain ⟨x, hx⟩ := Ka_irreducible a₂ a' ha
      rw [hx.2]
      exact ⟨x, .red_K x b', hx.1⟩
    case red_S a c =>
      obtain ⟨x, y, hx⟩ := Sab_irreducible a c a' ha
      rw [hx.2.2]
      refine ⟨x ⬝ b' ⬝ (y ⬝ b'), .red_S x y b', ?_⟩
      exact .par (.par hx.1 hb) (.par hx.2.1 hb)
  case red_I =>
    cases h₂
    case refl => exact ⟨a₁, .refl _, .red_I _⟩
    case par c a₁' hc ha =>
      rw [I_irreducible c hc]
      exact ⟨a₁', ha, .red_I a₁'⟩
    case red_I => exact ⟨a₁, .refl _, .refl _⟩
  case red_K c =>
    cases h₂
    case refl => exact ⟨a₁, .refl _, .red_K a₁ c⟩
    case par a' c' ha hc =>
      obtain ⟨x, hx⟩ := Ka_irreducible a₁ a' ha
      rw [hx.2]
      exact ⟨x, hx.1, .red_K x c'⟩
    case red_K => exact ⟨a₁, .refl _, .refl _⟩
  case red_S a b c =>
    cases h₂
    case refl => exact ⟨a ⬝ c ⬝ (b ⬝ c), .refl _, .red_S ..⟩
    case par d c' hd hc =>
      obtain ⟨x, y, hx⟩ := Sab_irreducible a b d hd
      rw [hx.2.2]
      exact ⟨x ⬝ c' ⬝ (y ⬝ c'), .par (.par hx.1 hc) (.par hx.2.1 hc), .red_S ..⟩
    case red_S => exact ⟨a ⬝ c ⬝ (b ⬝ c), .refl _, .refl _⟩
