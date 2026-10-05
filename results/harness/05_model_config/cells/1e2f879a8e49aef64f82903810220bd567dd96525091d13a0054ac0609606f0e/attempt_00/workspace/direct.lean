theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s₁ s₂ hr μ
  cases hr with
  | choice h =>
    constructor
    · intro s' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨t, ht, hb⟩ := h.follow_fst ht
        exact ⟨t, Tr.choiceL ht, .bisim hb⟩
      | choiceR ht => exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    · intro s' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨t, ht, hb⟩ := h.follow_snd ht
        exact ⟨t, Tr.choiceL ht, .bisim hb⟩
      | choiceR ht => exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro s' ht
      obtain ⟨t, ht, hb⟩ := h.follow_fst ht
      exact ⟨t, ht, .bisim hb⟩
    · intro s' ht
      obtain ⟨t, ht, hb⟩ := h.follow_snd ht
      exact ⟨t, ht, .bisim hb⟩
