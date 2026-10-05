theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁
  revert a₂
  induction h₁ <;> intro a₂ h₂
  case refl => exact ⟨_, h₂, .refl _⟩
  case par ha' hb' ih₁ ih₂ =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha' hb'⟩
    case par a'' b'' ha'' hb'' =>
      rcases ih₁ ha'' with ⟨a₃, ha, ha'₃⟩
      rcases ih₂ hb'' with ⟨b₃, hb, hb'₃⟩
      exact ⟨_, .par ha hb, .par ha'₃ hb'₃⟩
    case red_I =>
      cases I_irreducible _ ha'
      exact ⟨_, .red_I _, hb'⟩
    case red_K x y =>
      rcases Ka_irreducible _ _ ha' with ⟨_, h', rfl⟩
      exact ⟨_, .red_K _ _, h'⟩
    case red_S a c =>
      rcases Sab_irreducible _ _ _ ha' with ⟨_, _, ha, hc, rfl⟩
      exact ⟨_, .red_S .., .par (.par ha hb') (.par hc hb')⟩
  case red_I =>
    cases h₂ <;> try exact ⟨_, .refl _, .refl _⟩
    case refl => exact ⟨_, .refl _, .red_I _⟩
    case par c a₁' hc ha =>
      cases I_irreducible c hc
      exact ⟨_, ha, .red_I _⟩
  case red_K x y =>
    cases h₂ <;> try exact ⟨_, .refl _, .refl _⟩
    case refl => exact ⟨_, .refl _, .red_K _ _⟩
    case par a' c' ha hc =>
      rcases Ka_irreducible x a' ha with ⟨a₁', h', rfl⟩
      exact ⟨_, h', .red_K _ _⟩
  case red_S x y z =>
    cases h₂ <;> try exact ⟨_, .refl _, .refl _⟩
    case refl => exact ⟨_, .refl _, .red_S ..⟩
    case par d c' hd hc =>
      rcases Sab_irreducible x y d hd with ⟨a', b', ha, hb, rfl⟩
      exact ⟨_, .par (.par ha hc) (.par hb hc), .red_S ..⟩
