theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · intro a b hr
    cases hr <;> constructor <;> apply Bisimilarity.symm <;> assumption
  · intro a b hr μ t ht
    cases hr with
    | choice h =>
      cases ht with
      | choiceL ht =>
        exact (h.follow_fst ht).imp fun u hb => ⟨.choiceL hb.1, .bisim hb.2⟩
      | choiceR ht => exact ⟨t, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    | bisim h =>
      exact (h.follow_fst ht).imp fun u hb => ⟨hb.1, .bisim hb.2⟩
