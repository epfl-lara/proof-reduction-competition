theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  use @ChoiceBisim _ _ defs, ChoiceBisim.choice h
  intro s1 s2 hr μ
  grind [ChoiceBisim, IsBisimulation]
