lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have := der
  induction der <;> subst eq
  case var => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    rcases ih_l rfl l with val_l | ⟨t₁', red_l⟩
    · rcases ih_r rfl r with val_r | ⟨t₂', red_r⟩
      · obtain ⟨_, u, rfl⟩ := l.canonical_form_abs val_l
        exact .inr ⟨u ^ᵗᵗ t₂, .abs val_l.lc val_r⟩
      · exact .inr ⟨t₁.app t₂', .appᵣ val_l red_r⟩
    · exact .inr ⟨t₁'.app t₂, .appₗ r.wf.2.1 red_l⟩
  case tapp σ' der sub ih =>
    rcases ih rfl der with val | ⟨t', red⟩
    · obtain ⟨_, u, rfl⟩ := der.canonical_form_tabs val
      exact .inr ⟨u ^ᵗᵞ σ', .tabs val.lc (by grind)⟩
    · exact .inr ⟨.tapp t' σ', .tapp (by grind) red⟩
  case let' t₁ σ t₂ τ L der h ih _ =>
    have body : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
    rcases ih rfl der with val | ⟨t', red⟩
    · exact .inr ⟨t₂ ^ᵗᵗ t₁, .let_body val body⟩
    · exact .inr ⟨t'.let' t₂, .let_bind red body⟩
  case inl der _ ih =>
    rcases ih rfl der with val | ⟨t', red⟩
    · exact .inl (Value.inl val)
    · exact .inr ⟨.inl t', .inl red⟩
  case inr der _ ih =>
    rcases ih rfl der with val | ⟨t', red⟩
    · exact .inl (Value.inr val)
    · exact .inr ⟨.inr t', .inr red⟩
  case case t₁ _ _ t₂ _ t₃ _ der _ _ ih _ _ =>
    have body₂ : t₂.body := by grind
    have body₃ : t₃.body := by grind
    rcases ih rfl der with val | ⟨t', red⟩
    · rcases der.canonical_form_sum val with ⟨u, rfl | rfl⟩
      · cases val with
        | inl vu => exact .inr ⟨t₂ ^ᵗᵗ u, .case_inl vu body₂ body₃⟩
      · cases val with
        | inr vu => exact .inr ⟨t₃ ^ᵗᵗ u, .case_inr vu body₂ body₃⟩
    · exact .inr ⟨t'.case t₂ t₃, .case red body₂ body₃⟩
  case sub => grind
  case abs σ _ τ L _ _=>
    left
    constructor
    apply LC.abs L
    · grind only [→ wf, cases Term.LC]
    · grind
  case tabs L _ _=>
    left
    constructor
    apply LC.tabs L
    · grind only [→ wf, cases Term.LC]
    · grind