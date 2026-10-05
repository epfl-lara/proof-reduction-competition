theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro a b hr μ
  cases hr with
  | choice h =>
    constructor
    · intro s ht
      cases ht with
      | choiceL ht =>
        obtain ⟨t, ht, hh⟩ := h.follow_fst ht
        exact ⟨t, .choiceL ht, .bisim hh⟩
      | choiceR ht => exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    · intro s ht
      cases ht with
      | choiceL ht =>
        obtain ⟨t, ht, hh⟩ := h.follow_snd ht
        exact ⟨t, .choiceL ht, .bisim hh⟩
      | choiceR ht => exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro s ht
      obtain ⟨t, ht, hh⟩ := h.follow_fst ht
      exact ⟨t, ht, .bisim hh⟩
    · intro s ht
      obtain ⟨t, ht, hh⟩ := h.follow_snd ht
      exact ⟨t, ht, .bisim hh⟩
