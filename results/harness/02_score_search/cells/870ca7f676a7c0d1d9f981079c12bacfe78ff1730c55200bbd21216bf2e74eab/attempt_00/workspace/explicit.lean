theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s t h μ
  cases h with
  | choice h =>
    constructor
    · intro s' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨t', ht', h'⟩ := h.follow_fst ht
        exact ⟨t', .choiceL ht', .bisim h'⟩
      | choiceR ht => exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    · intro t' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨s', ht', h'⟩ := h.follow_snd ht
        exact ⟨s', .choiceL ht', .bisim h'⟩
      | choiceR ht => exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro s' ht
      obtain ⟨t', ht', h'⟩ := h.follow_fst ht
      exact ⟨t', ht', .bisim h'⟩
    · intro t' ht
      obtain ⟨s', ht', h'⟩ := h.follow_snd ht
      exact ⟨s', ht', .bisim h'⟩
