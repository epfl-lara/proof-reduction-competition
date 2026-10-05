theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  exists ChoiceBisim, ChoiceBisim.choice h
  intro a b hr μ
  constructor <;> intro s ht <;> rcases hr with h | h
  all_goals try (case' choice => cases ht)
  all_goals
    first
    | exact ⟨s, .choiceR ‹_›, .bisim (HomBisimilarity.refl s)⟩
    | obtain ⟨t, ht, hh⟩ := (by first | exact h.follow_fst ‹_› | exact h.follow_snd ‹_›)
      refine ⟨t, ?_, .bisim hh⟩
      first | exact ht | exact .choiceL ht