theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro hpq
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice hpq, ⟨?_⟩, ?_⟩
  · intro s t h
    cases h <;> constructor <;> exact Bisimilarity.symm (by assumption)
  · intro s t hr μ u ht
    cases hr <;> rename_i h
    case' choice => cases ht <;> rename_i ht
    case choice.choiceR =>
      exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    all_goals
      obtain ⟨v, hv, hb⟩ := h.follow_fst ht
      refine ⟨v, ?_, .bisim hb⟩
      first | exact hv | exact .choiceL hv
