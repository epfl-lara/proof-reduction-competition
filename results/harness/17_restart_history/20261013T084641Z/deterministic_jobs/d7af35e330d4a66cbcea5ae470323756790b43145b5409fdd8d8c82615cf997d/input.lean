theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  exists _, ChoiceBisim.choice h
  constructor
  · constructor
    grind only [ChoiceBisim, → Bisimilarity.symm]
  rintro s t (h | h) μ s' ht
  case' choice =>
    cases ht <;> rename_i ht
  case choice.choiceR =>
    exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    obtain ⟨t', ht', h'⟩ := h.follow_fst ht
    refine ⟨t', ?_, .bisim h'⟩
    try apply Tr.choiceL
    exact ht'