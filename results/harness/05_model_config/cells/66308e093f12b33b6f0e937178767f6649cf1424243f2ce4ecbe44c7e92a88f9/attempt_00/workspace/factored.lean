theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, ChoiceBisim.choice h, ?_⟩
  intro s t hr μ
  constructor <;> intro u ht <;> cases hr <;> rename_i h
  case' left.choice | right.choice =>
    cases ht
    case choiceR ht =>
      exact ⟨u, Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    case' choiceL ht => skip
  all_goals
    obtain ⟨v, hv, hb⟩ := (by first | exact h.follow_fst ht | exact h.follow_snd ht)
    first
    | exact ⟨v, Tr.choiceL hv, ChoiceBisim.bisim hb⟩
    | exact ⟨v, hv, ChoiceBisim.bisim hb⟩
