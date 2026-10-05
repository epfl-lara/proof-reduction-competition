lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => cases mem
  case abs | tabs => left; constructor; exact der'.wf.2.1
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    have := r.wf.2.1
    specialize ih_l rfl l
    specialize ih_r rfl r
    grind only [→ l.canonical_form_abs, Value.lc, → Red.abs,
      → Red.appₗ (t₁ := t₁), → Red.appᵣ (t₂ := t₂)]
  case tapp d _ ih =>
    cases der'.wf.2.1 with | tapp _ lc =>
      specialize ih rfl d
      grind only [→ d.canonical_form_tabs, → Red.tabs, → Red.tapp]
  case let' d _ ih _ =>
    have := body_let.mp der'.wf.2.1
    specialize ih rfl d
    grind only [→ Red.let_body, → Red.let_bind]
  case inl | inr | sub =>
    rename_i d _ ih
    specialize ih rfl d
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  case case t₁ _ _ _ _ _ _ d _ _ ih _ _ =>
    have := body_case.mp der'.wf.2.1
    specialize ih rfl d
    grind only [→ d.canonical_form_sum, cases Value, → Red.case (t₁ := t₁),
      → Red.case_inl, → Red.case_inr]
