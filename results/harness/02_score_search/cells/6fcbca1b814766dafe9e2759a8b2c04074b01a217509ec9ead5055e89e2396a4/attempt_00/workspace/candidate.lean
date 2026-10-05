theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  have join {x y} (h : ParallelReduction y x) : Join ParallelReduction x y :=
    ⟨x, .refl _, h⟩
  induction h₁ generalizing a₂
  case refl => exact ⟨_, h₂, .refl _⟩
  case par a a' b b' ha hb ih_a ih_b =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par a'' b'' ha' hb' =>
      rcases ih_a ha' with ⟨x, h₁, h₂⟩
      rcases ih_b hb' with ⟨y, h₃, h₄⟩
      exact ⟨_, .par h₁ h₃, .par h₂ h₄⟩
    case red_I =>
      cases ha
      exact ⟨_, .red_I .., hb⟩
    case red_K =>
      rcases Ka_irreducible a₂ a' ha with ⟨x, hx, rfl⟩
      exact ⟨_, .red_K .., hx⟩
    case red_S x z =>
      rcases Sab_irreducible x z a' ha with ⟨x', z', hx, hz, rfl⟩
      exact ⟨_, .red_S ..,
        .par (.par hx hb) (.par hz hb)⟩
  case red_I x =>
    cases h₂
    case refl => exact join (.red_I ..)
    case par c d hc hd =>
      cases hc
      exact ⟨_, hd, .red_I _⟩
    case red_I => exact join (.refl x)
  case red_K x y =>
    cases h₂
    case refl => exact join (.red_K ..)
    case par d z hd hz =>
      rcases Ka_irreducible x d hd with ⟨x', hx, rfl⟩
      exact ⟨_, hx, .red_K ..⟩
    case red_K => exact join (.refl x)
  case red_S x y z =>
    cases h₂
    case refl => exact join (.red_S ..)
    case par d z' hd hz =>
      rcases Sab_irreducible x y d hd with ⟨x', y', hx, hy, rfl⟩
      exact ⟨_, .par (.par hx hz) (.par hy hz), .red_S ..⟩
    case red_S => exact join (.refl _)

