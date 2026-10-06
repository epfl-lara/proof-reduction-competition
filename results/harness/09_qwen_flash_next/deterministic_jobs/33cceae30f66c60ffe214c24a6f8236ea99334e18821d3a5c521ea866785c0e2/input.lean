theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨ChoiceBisim, .choice h, ?_⟩
  intro _ _ hr _
  cases hr with
  | bisim => grind [ChoiceBisim, Bisimilarity.follow_fst, Bisimilarity.follow_snd]
  | choice hb =>
    constructor <;> intro x htr <;> cases htr with
      | choiceR h => exact ⟨_, .choiceR h, .bisim (.refl _)⟩
      | choiceL h => first
        | exact (hb.follow_fst h).imp fun _ ⟨hy, hr'⟩ => ⟨.choiceL hy, .bisim hr'⟩
        | exact (hb.follow_snd h).imp fun _ ⟨hy, hr'⟩ => ⟨.choiceL hy, .bisim hr'⟩