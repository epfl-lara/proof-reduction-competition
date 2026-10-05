theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · intro a b hr
    cases hr with
    | choice h => exact .choice h.symm
    | bisim h => exact .bisim h.symm
  · intro a b hr μ t ht
    cases hr with
    | choice h =>
      cases ht with
      | choiceL ht =>
        obtain ⟨u, hu, hb⟩ := h.follow_fst ht
        exact ⟨u, .choiceL hu, .bisim hb⟩
      | choiceR ht => exact ⟨t, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    | bisim h =>
      obtain ⟨u, hu, hb⟩ := h.follow_fst ht
      exact ⟨u, hu, .bisim hb⟩
