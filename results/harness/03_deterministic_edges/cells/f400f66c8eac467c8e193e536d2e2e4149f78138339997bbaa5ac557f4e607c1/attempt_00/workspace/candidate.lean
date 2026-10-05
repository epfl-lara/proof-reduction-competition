theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  rw [HomBisimilarity.symm_simulation]
  refine ⟨_, ChoiceBisim.choice h, ⟨?_⟩, ?_⟩
  · rintro s t (h | h) <;> constructor <;> exact h.symm
  rintro s t (h | h) μ u ht
  case' choice => cases ht
  case choiceR => exact ⟨_, Tr.choiceR ‹_›, .bisim (HomBisimilarity.refl _)⟩
  all_goals
    refine (h.follow_fst ‹_›).imp fun _ => And.imp ?_ ChoiceBisim.bisim
    first | exact id | exact Tr.choiceL
