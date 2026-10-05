theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · intro s t hr
    cases hr <;> constructor <;> exact Bisimilarity.symm ‹_›
  intro s t hr μ u ht
  cases hr <;> rename_i h
  case' choice => cases ht <;> rename_i ht
  case choiceR => exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    obtain ⟨v, hv, hb⟩ := h.follow_fst ht
    exact ⟨v, by first | exact hv | exact Tr.choiceL hv, .bisim hb⟩
