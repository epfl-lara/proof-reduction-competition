theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s t h μ
  constructor <;> intro u ht <;> cases h with
  | choice h =>
    cases ht with
    | choiceL ht =>
      first
      | refine (h.follow_fst ht).elim ?_
      | refine (h.follow_snd ht).elim ?_
      rintro v ⟨hv, h⟩
      exact ⟨v, .choiceL hv, .bisim h⟩
    | choiceR ht => exact ⟨_, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    first
    | refine (h.follow_fst ht).elim ?_
    | refine (h.follow_snd ht).elim ?_
    rintro v ⟨hv, h⟩
    exact ⟨v, hv, .bisim h⟩
