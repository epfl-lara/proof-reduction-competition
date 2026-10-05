theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s1 s2 hr μ
  cases hr with
  | choice h =>
    constructor <;> intro s' htr <;> cases htr with
    | choiceL ht =>
      first
      | obtain ⟨s2', ht', hr'⟩ := h.follow_fst ht
        exact ⟨s2', Tr.choiceL ht', .bisim hr'⟩
      | obtain ⟨s1', ht', hr'⟩ := h.follow_snd ht
        exact ⟨s1', Tr.choiceL ht', .bisim hr'⟩
    | choiceR ht => exact ⟨s', Tr.choiceR ht, .bisim (HomBisimilarity.refl s')⟩
  | bisim h => grind [ChoiceBisim, IsBisimulation]
