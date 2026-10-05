theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro hpq
  refine ⟨@ChoiceBisim _ _ defs, .choice hpq, ?_⟩
  intro s t hr μ
  constructor <;> intro u ht <;> cases hr <;> rename_i h
  case' left.choice | right.choice =>
    cases ht <;> rename_i ht
  case left.choice.choiceR | right.choice.choiceR =>
    exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    first
    | refine (h.follow_fst ht).elim ?_
    | refine (h.follow_snd ht).elim ?_
    rintro v ⟨hv, hb⟩
    refine ⟨v, ?_, .bisim hb⟩
    first | exact hv | exact .choiceL hv
