theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, ChoiceBisim.choice h, ?_⟩
  intro s t hr μ
  constructor <;> intro u ht
  · cases hr with
    | choice h =>
      cases ht with
      | choiceL ht =>
        obtain ⟨v, hv, hb⟩ := h.follow_fst ht
        exact ⟨v, Tr.choiceL hv, ChoiceBisim.bisim hb⟩
      | choiceR ht =>
        exact ⟨u, Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    | bisim h =>
      obtain ⟨v, hv, hb⟩ := h.follow_fst ht
      exact ⟨v, hv, ChoiceBisim.bisim hb⟩
  · cases hr with
    | choice h =>
      cases ht with
      | choiceL ht =>
        obtain ⟨v, hv, hb⟩ := h.follow_snd ht
        exact ⟨v, Tr.choiceL hv, ChoiceBisim.bisim hb⟩
      | choiceR ht =>
        exact ⟨u, Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    | bisim h =>
      obtain ⟨v, hv, hb⟩ := h.follow_snd ht
      exact ⟨v, hv, ChoiceBisim.bisim hb⟩