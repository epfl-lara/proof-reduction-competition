theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · intro s t hr
    cases hr with
    | choice h => exact .choice h.symm
    | bisim h => exact .bisim h.symm
  intro s t hr μ u ht
  cases hr with
  | choice h =>
    cases ht with
    | choiceL ht =>
      obtain ⟨v, hv, hb⟩ := h.follow_fst ht
      exact ⟨v, Tr.choiceL hv, .bisim hb⟩
    | choiceR ht => exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    obtain ⟨v, hv, hb⟩ := h.follow_fst ht
    exact ⟨v, hv, .bisim hb⟩
