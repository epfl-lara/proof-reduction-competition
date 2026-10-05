lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    cases ih_l rfl l with
    | inl val_l =>
        cases ih_r rfl r with
        | inl val_r =>
            obtain ⟨σ, u, h⟩ := l.canonical_form_abs val_l
            exists u ^ᵗᵗ t₂
            rw [h]
            exact Red.abs (h ▸ l.wf.2.1) val_r
        | inr red_r =>
            obtain ⟨t₂', red⟩ := red_r
            exact ⟨t₁.app t₂', Red.appᵣ val_l red⟩
    | inr red_l =>
        obtain ⟨t₁', red⟩ := red_l
        exact ⟨t₁'.app t₂, Red.appₗ r.wf.2.1 red⟩
  case tapp σ' der _ ih =>
    right
    specialize ih rfl der
    cases ih with
    | inl val =>
        obtain ⟨_, t, _⟩ := der.canonical_form_tabs val
        exists t ^ᵗᵞ σ'
        grind
    | inr red =>
        obtain ⟨t', _⟩ := red
        exists .tapp t' σ'
        grind
  case let' t₁ σ t₂ τ L der h ih _ =>
    have hb : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
    cases ih rfl der with
    | inl val => exact Or.inr ⟨t₂ ^ᵗᵗ t₁, Red.let_body val hb⟩
    | inr red =>
        obtain ⟨t₁', step⟩ := red
        exact Or.inr ⟨t₁'.let' t₂, Red.let_bind step hb⟩
  case inl der _ ih =>
    cases (ih rfl der) with
    | inl val => grind
    | inr red =>
        right
        obtain ⟨t', _⟩ := red
        exists .inl t'
        grind
  case inr der _ ih =>
    cases (ih rfl der) with
    | inl val => grind
    | inr red =>
        right
        obtain ⟨t', _⟩ := red
        exists .inr t'
        grind
  case case t₁ _ _ t₂ _ t₃ _ der _ _ ih _ _ =>
    right
    cases ih rfl der with
    | inl val =>
        have ⟨t₁, lr⟩ := der.canonical_form_sum val
        cases lr <;> [exists t₂ ^ᵗᵗ t₁; exists t₃ ^ᵗᵗ t₁] <;> grind
    | inr red =>
        obtain ⟨t₁', _⟩ := red
        exists t₁'.case t₂ t₃
        grind
  case sub der sub ih => exact ih rfl der
  case abs σ body τ L h ih =>
    grind
  case tabs L h ih =>
    grind