theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  have join_refl (x) : Join ParallelReduction x x := ⟨x, .refl _, .refl _⟩
  cases h₁
  case refl => exact ⟨_, h₂, .refl _⟩
  case par a a' b b' ha' hb' =>
    cases h₂
    case refl => exact ⟨_, .refl _, .par ha' hb'⟩
    case par a'' b'' ha'' hb'' =>
      let ⟨a₃, ha⟩ := parallelReduction_diamond ha' ha''
      let ⟨b₃, hb⟩ := parallelReduction_diamond hb' hb''
      exact ⟨a₃ ⬝ b₃, .par ha.1 hb.1, .par ha.2 hb.2⟩
    case red_I =>
      rcases I_irreducible a' ha' with rfl
      exact ⟨b', .red_I b', hb'⟩
    case red_K =>
      rcases Ka_irreducible a₂ a' ha' with ⟨a₂', ha₂', rfl⟩
      exact ⟨a₂', .red_K .., ha₂'⟩
    case red_S a c =>
      rcases Sab_irreducible a c a' ha' with ⟨a'', c', ha, hc, rfl⟩
      exact ⟨a'' ⬝ b' ⬝ (c' ⬝ b'), .red_S a'' c' b', .par (.par ha hb') (.par hc hb')⟩
  case red_I =>
    cases h₂
    case refl => exact ⟨a₁, .refl _, .red_I _⟩
    case par c a₁' hc ha =>
      rcases I_irreducible c hc with rfl
      exact ⟨a₁', ha, .red_I _⟩
    case red_I => exact join_refl _
  case red_K c =>
    cases h₂
    case refl => exact ⟨_, .refl _, .red_K ..⟩
    case par a' c' ha hc =>
      rcases Ka_irreducible a₁ a' ha with ⟨a₁', h', rfl⟩
      exact ⟨a₁', h', .red_K ..⟩
    case red_K => exact join_refl _
  case red_S a b c =>
    cases h₂
    case refl => exact ⟨a ⬝ c ⬝ (b ⬝ c), .refl _, .red_S ..⟩
    case par d c' hd hc =>
      rcases Sab_irreducible a b d hd with ⟨a', b', ha, hb, rfl⟩
      exact ⟨a' ⬝ c' ⬝ (b' ⬝ c'), .par (.par ha hc) (.par hb hc), .red_S ..⟩
    case red_S => exact join_refl _
