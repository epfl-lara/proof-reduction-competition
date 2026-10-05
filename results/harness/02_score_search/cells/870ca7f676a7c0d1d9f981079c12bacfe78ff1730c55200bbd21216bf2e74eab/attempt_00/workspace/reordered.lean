theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro hpq
  refine ⟨@ChoiceBisim _ _ defs, .choice hpq, ?_⟩
  intro s t hr μ
  cases hr <;> rename_i h <;> constructor <;> intro u ht
  case' choice.left | choice.right =>
    cases ht <;> rename_i ht
  case choice.left.choiceR | choice.right.choiceR =>
    exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    first
    | refine (h.follow_fst ht).elim ?_
    | refine (h.follow_snd ht).elim ?_
    rintro v ⟨hv, hb⟩
    refine ⟨v, ?_, .bisim hb⟩
    first | exact hv | exact .choiceL hv
