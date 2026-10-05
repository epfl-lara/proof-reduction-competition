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
    | apply (h.follow_fst ht).imp
    | apply (h.follow_snd ht).imp
    intro t
    refine And.imp ?_ ChoiceBisim.bisim
    first | exact id | exact Tr.choiceL
