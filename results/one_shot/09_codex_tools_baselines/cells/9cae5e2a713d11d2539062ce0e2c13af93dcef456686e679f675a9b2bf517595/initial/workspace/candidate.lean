lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => simp at mem
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    rcases ih_l rfl with val_l | ⟨u, red_l⟩
    · rcases ih_r rfl with val_r | ⟨v, red_r⟩
      · obtain ⟨_, u, rfl⟩ := l.canonical_form_abs val_l
        exact Or.inr ⟨u ^ᵗᵗ t₂, Red.abs val_l.lc val_r⟩
      · exact Or.inr ⟨t₁.app v, Red.appᵣ val_l red_r⟩
    · exact Or.inr ⟨u.app t₂, Red.appₗ r.wf.2.1 red_l⟩
  case tapp σ' d sub ih =>
    rcases ih rfl with val | ⟨u, red⟩
    · obtain ⟨_, u, rfl⟩ := d.canonical_form_tabs val
      exact Or.inr ⟨u ^ᵗᵞ σ', Red.tabs val.lc sub.wf.2.1.lc⟩
    · exact Or.inr ⟨.tapp u σ', Red.tapp sub.wf.2.1.lc red⟩
  case let' t₁ σ t₂ τ L d body ih _ =>
    have hb : t₂.body := ⟨L, fun x hx => (body x hx).wf.2.1⟩
    rcases ih rfl with val | ⟨u, red⟩
    · exact Or.inr ⟨t₂ ^ᵗᵗ t₁, Red.let_body val hb⟩
    · exact Or.inr ⟨u.let' t₂, Red.let_bind red hb⟩
  case inl d _ ih =>
    rcases ih rfl with val | ⟨u, red⟩
    · exact Or.inl (.inl val)
    · exact Or.inr ⟨.inl u, Red.inl red⟩
  case inr d _ ih =>
    rcases ih rfl with val | ⟨u, red⟩
    · exact Or.inl (.inr val)
    · exact Or.inr ⟨.inr u, Red.inr red⟩
  case case t₁ _ _ t₂ _ t₃ _ d body₂ body₃ ih _ _ =>
    have h₂ : t₂.body := ⟨_, fun x hx => (body₂ x hx).wf.2.1⟩
    have h₃ : t₃.body := ⟨_, fun x hx => (body₃ x hx).wf.2.1⟩
    rcases ih rfl with val | ⟨u, red⟩
    · obtain ⟨s, h | h⟩ := d.canonical_form_sum val
      · subst t₁
        cases val with
        | inl v => exact Or.inr ⟨t₂ ^ᵗᵗ s, Red.case_inl v h₂ h₃⟩
      · subst t₁
        cases val with
        | inr v => exact Or.inr ⟨t₃ ^ᵗᵗ s, Red.case_inr v h₂ h₃⟩
    · exact Or.inr ⟨u.case t₂ t₃, Red.case red h₂ h₃⟩
  case sub => grind
  case abs σ t₁ τ L body _ =>
    left
    constructor
    apply LC.abs L
    · obtain ⟨x, hx⟩ := fresh_exists L
      exact (Ty.Wf.of_env_ty (body x hx).wf.1).lc
    · intro x hx
      exact (body x hx).wf.2.1
  case tabs L body _ =>
    left
    constructor
    apply LC.tabs L
    · obtain ⟨X, hX⟩ := fresh_exists L
      exact (Ty.Wf.of_env_sub (body X hX).wf.1).lc
    · intro X hX
      exact (body X hX).wf.2.1
