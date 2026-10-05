theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a b c h k
  induction h generalizing c
  case refl => exact ⟨c, k, .refl _⟩
  case par a a' b b' ha hb ih jh =>
    cases k
    case refl => exact ⟨_, .refl _, .par ha hb⟩
    case par hc hd =>
      obtain ⟨x, hx, hx'⟩ := ih hc
      obtain ⟨y, hy, hy'⟩ := jh hd
      exact ⟨_, .par hx hy, .par hx' hy'⟩
    case red_I =>
      cases I_irreducible _ ha
      exact ⟨_, .red_I _, hb⟩
    case red_K =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ ha
      exact ⟨_, .red_K _ _, hx⟩
    case red_S =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ ha
      exact ⟨_, .red_S _ _ _, .par (.par hx hb) (.par hy hb)⟩
  case red_I =>
    cases k
    case refl => exact ⟨_, .refl _, .red_I _⟩
    case red_I => exact ⟨_, .refl _, .refl _⟩
    case par hc hd =>
      cases I_irreducible _ hc
      exact ⟨_, hd, .red_I _⟩
  case red_K =>
    cases k
    case refl => exact ⟨_, .refl _, .red_K _ _⟩
    case red_K => exact ⟨_, .refl _, .refl _⟩
    case par hc hd =>
      obtain ⟨x, hx, rfl⟩ := Ka_irreducible _ _ hc
      exact ⟨_, hx, .red_K _ _⟩
  case red_S =>
    cases k
    case refl => exact ⟨_, .refl _, .red_S _ _ _⟩
    case red_S => exact ⟨_, .refl _, .refl _⟩
    case par hc hd =>
      obtain ⟨x, y, hx, hy, rfl⟩ := Sab_irreducible _ _ _ hc
      exact ⟨_, .par (.par hx hd) (.par hy hd), .red_S _ _ _⟩
