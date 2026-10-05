theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, ChoiceBisim.choice h, ?_⟩
  intro s t hr μ
  constructor <;> intro u ht <;> cases hr with
  | choice h =>
    cases ht with
    | choiceL ht =>
      first | refine (h.follow_fst ht).elim ?_
            | refine (h.follow_snd ht).elim ?_
      rintro v ⟨hv, hb⟩
      exact ⟨v, Tr.choiceL hv, ChoiceBisim.bisim hb⟩
    | choiceR ht =>
      exact ⟨u, Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    first | refine (h.follow_fst ht).elim ?_
          | refine (h.follow_snd ht).elim ?_
    rintro v ⟨hv, hb⟩
    exact ⟨v, hv, ChoiceBisim.bisim hb⟩