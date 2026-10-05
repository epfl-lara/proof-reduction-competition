theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s₁ s₂ hr μ
  cases hr
  case' choice h =>
    constructor <;> intro s' ht <;> cases ht
    all_goals
      rename_i ht
      try exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  case' bisim h => constructor <;> intro s' ht
  all_goals
    first
    | apply (h.follow_fst ht).elim
    | apply (h.follow_snd ht).elim
    rintro t ⟨ht, hb⟩
    first
    | exact ⟨t, Tr.choiceL ht, .bisim hb⟩
    | exact ⟨t, ht, .bisim hb⟩
