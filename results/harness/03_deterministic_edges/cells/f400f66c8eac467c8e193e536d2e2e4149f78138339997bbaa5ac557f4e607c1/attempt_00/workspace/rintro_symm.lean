theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · rintro s t (h | h) <;> constructor <;> exact h.symm
  rintro s t (h | h) μ u ht
  case' choice => cases ht <;> rename_i ht
  case choiceR => exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    obtain ⟨v, hv, hb⟩ := h.follow_fst ht
    exact ⟨v, by first | exact hv | exact Tr.choiceL hv, .bisim hb⟩
