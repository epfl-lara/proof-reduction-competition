theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s t hr μ
  cases hr <;> rename_i h <;> constructor <;> intro u ht
  case' choice.left | choice.right => cases ht <;> rename_i ht
  case choice.left.choiceR | choice.right.choiceR =>
    exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  case' choice.left.choiceL | bisim.left => obtain ⟨v, hv, hb⟩ := h.follow_fst ht
  case' choice.right.choiceL | bisim.right => obtain ⟨v, hv, hb⟩ := h.follow_snd ht
  all_goals exact ⟨v, by first | exact hv | exact Tr.choiceL hv, .bisim hb⟩
