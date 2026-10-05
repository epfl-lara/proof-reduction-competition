theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨ChoiceBisim, .choice h, ⟨?_⟩, ?_⟩
  · grind only [ChoiceBisim, → Bisimilarity.symm]
  · rintro _ _ (h | h) μ s' ht
    case' choice => cases ht <;> rename_i ht
    case choiceR => exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    all_goals
      apply (h.follow_fst ht).imp
      intro t
      refine And.imp ?_ ChoiceBisim.bisim
      first | exact id | exact Tr.choiceL