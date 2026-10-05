theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ⟨?_⟩, ?_⟩
  · intro a b hr
    cases hr <;> constructor <;> apply Bisimilarity.symm <;> assumption
  · intro a b hr μ t ht
    cases hr <;> rename_i h
    case' choice =>
      cases ht
      case choiceR ht => exact ⟨t, .choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    all_goals
      exact (h.follow_fst (by assumption)).imp fun u hb =>
        ⟨by solve_by_elim only [hb.1, Tr.choiceL], .bisim hb.2⟩
