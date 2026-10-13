theorem parallelReduction_diamond : Diamond ParallelReduction := by
  intro a a₁ a₂ h₁ h₂
  induction h₁ generalizing a₂
  case refl =>
    econstructor
    constructor
    exact h₂
    constructor
  case' par ha hb iha ihb => skip
  all_goals cases h₂
  case par.par ha' hb' =>
    obtain ⟨_, hc⟩ := iha ha'
    obtain ⟨_, hd⟩ := ihb hb'
    econstructor
    constructor
    exact hc.1.par hd.1
    exact hc.2.par hd.2
  case' red_I.par | red_K.par | red_S.par =>
    rename_i ha hb
    apply symm
  case par.red_I | red_I.par =>
    cases I_irreducible _ ha
    econstructor
    constructor
    apply ParallelReduction.red_I
    exact hb
  case par.red_K | red_K.par =>
    obtain ⟨_, h, rfl⟩ := Ka_irreducible _ _ ha
    econstructor
    constructor
    apply ParallelReduction.red_K
    exact h
  case par.red_S | red_S.par =>
    obtain ⟨_, _, h, h', rfl⟩ := Sab_irreducible _ _ _ ha
    econstructor
    constructor
    apply ParallelReduction.red_S
    exact (h.par hb).par (h'.par hb)
  iterate 3 all_goals econstructor
  all_goals assumption