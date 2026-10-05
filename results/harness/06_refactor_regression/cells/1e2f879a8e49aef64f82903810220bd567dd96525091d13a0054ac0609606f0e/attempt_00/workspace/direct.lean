theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s1 s2 hr μ
  cases hr with
  | choice h =>
    constructor
    · intro t ht
      cases ht with
      | choiceL ht =>
        obtain ⟨u, hu, hb⟩ := h.follow_fst ht
        exact ⟨u, .choiceL hu, .bisim hb⟩
      | choiceR ht => exact ⟨t, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    · intro t ht
      cases ht with
      | choiceL ht =>
        obtain ⟨u, hu, hb⟩ := h.follow_snd ht
        exact ⟨u, .choiceL hu, .bisim hb⟩
      | choiceR ht => exact ⟨t, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro t ht
      obtain ⟨u, hu, hb⟩ := h.follow_fst ht
      exact ⟨u, hu, .bisim hb⟩
    · intro t ht
      obtain ⟨u, hu, hb⟩ := h.follow_snd ht
      exact ⟨u, hu, .bisim hb⟩
