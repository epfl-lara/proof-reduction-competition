theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨_, ChoiceBisim.choice h, ⟨?_⟩, ?_⟩
  · grind only [ChoiceBisim, → Bisimilarity.symm]
  · rintro s1 s2 (hb | hb) μ s' ht
    case' choice => cases ht <;> rename_i ht
    case choiceR =>
      exact ⟨s', Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    all_goals
      refine (hb.follow_fst ht).imp fun _ h => ⟨?_, ChoiceBisim.bisim h.2⟩
      solve_by_elim only [h.1, Tr.choiceL]