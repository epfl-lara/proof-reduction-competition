theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s t hr μ
  cases hr with
  | choice h =>
    constructor <;> intro u ht <;> cases ht with
    | choiceL ht =>
      first
      | obtain ⟨v, hv, hb⟩ := h.follow_fst ht
        exact ⟨v, Tr.choiceL hv, .bisim hb⟩
      | obtain ⟨v, hv, hb⟩ := h.follow_snd ht
        exact ⟨v, Tr.choiceL hv, .bisim hb⟩
    | choiceR ht => exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor <;> intro u ht
    · obtain ⟨v, hv, hb⟩ := h.follow_fst ht
      exact ⟨v, hv, .bisim hb⟩
    · obtain ⟨v, hv, hb⟩ := h.follow_snd ht
      exact ⟨v, hv, .bisim hb⟩
