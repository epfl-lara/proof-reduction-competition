theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro hpq
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice hpq, ⟨?_⟩, ?_⟩
  · rintro _ _ (h | h) <;> constructor <;> exact h.symm
  · rintro _ _ (h | h) μ u ht
    case' choice => cases ht <;> rename_i ht
    case choice.choiceR =>
      exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    all_goals
      obtain ⟨v, hv, hb⟩ := h.follow_fst ht
      refine ⟨v, ?_, .bisim hb⟩
      first | exact hv | exact .choiceL hv
