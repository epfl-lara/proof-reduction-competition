theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨ChoiceBisim, .choice h, ?_⟩
  rintro _ _ (h | h) μ
  all_goals constructor <;> intro s' ht
  case' choice.left | choice.right =>
    cases ht <;> rename_i ht
  case choiceR | choiceR =>
    exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    first
    | apply (h.follow_fst ht).elim
    | apply (h.follow_snd ht).elim
    rintro t ⟨ht, hb⟩
    refine ⟨t, ?_, .bisim hb⟩
    solve_by_elim only [ht, Tr.choiceL]
