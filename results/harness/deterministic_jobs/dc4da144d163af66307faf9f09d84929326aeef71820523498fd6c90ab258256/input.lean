theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨ChoiceBisim, .choice h, ?_⟩
  intro a b hr μ
  constructor <;> intro s ht <;> cases hr <;> rename_i h
  all_goals try (case' choice => cases ht)
  all_goals
    first
    | exact ⟨s, .choiceR ‹_›, .bisim (HomBisimilarity.refl s)⟩
    | obtain ⟨t, ht, hh⟩ := (by first | exact h.follow_fst ‹_› | exact h.follow_snd ‹_›)
      refine ⟨t, ?_, .bisim hh⟩
      first | exact ht | exact .choiceL ht