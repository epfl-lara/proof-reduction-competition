theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, ChoiceBisim.choice h, ?_⟩
  intro s t hr μ
  constructor <;> intro u ht <;> cases hr with
  | choice h =>
    cases ht with
    | choiceL ht => _
    | choiceR ht =>
      exact ⟨u, Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
  | bisim h => _
  all_goals
    obtain ⟨v, hv, hr⟩ := by first | exact h.follow_fst ht | exact h.follow_snd ht
    exact ⟨v, by first | exact hv | exact Tr.choiceL hv, ChoiceBisim.bisim hr⟩
