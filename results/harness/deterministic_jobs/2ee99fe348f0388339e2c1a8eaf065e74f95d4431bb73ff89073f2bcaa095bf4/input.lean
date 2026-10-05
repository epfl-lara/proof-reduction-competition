theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro a b hr μ
  cases hr <;> rename_i h <;> constructor <;> intro s ht
  case' choice.left => cases ht
  case' choice.right => cases ht
  all_goals
    first
    | exact ⟨_, .choiceR ‹_›, .bisim (HomBisimilarity.refl _)⟩
    | obtain ⟨t, ht, hh⟩ := (by first | exact h.follow_fst ‹_› | exact h.follow_snd ‹_›)
      refine ⟨t, ?_, .bisim hh⟩
      solve_by_elim [Tr.choiceL]