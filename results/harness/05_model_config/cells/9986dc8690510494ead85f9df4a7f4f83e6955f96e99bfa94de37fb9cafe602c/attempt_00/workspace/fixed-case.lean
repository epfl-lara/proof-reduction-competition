lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => cases mem
  case abs | tabs => left; constructor; exact der'.wf.2.1
  case app l r ih_l ih_r =>
    right
    have lc := r.wf.2.1
    rcases ih_l rfl l with h | ⟨_, h⟩ <;>
      rcases ih_r rfl r with h' | ⟨_, h'⟩
    · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs h
      exact ⟨_, .abs h.lc h'⟩
    all_goals exact ⟨_, by solve_by_elim [Red.appₗ, Red.appᵣ]⟩
  case tapp d _ ih =>
    cases der'.wf.2.1 with | tapp _ lc =>
      specialize ih rfl d
      grind only [→ canonical_form_tabs, → Red.tabs, → Red.tapp]
  case let' d _ ih _ =>
    have body := (body_let.mp der'.wf.2.1).2
    specialize ih rfl d
    grind only [→ Red.let_body, → Red.let_bind]
  case inl | inr | sub =>
    rename_i d _ ih
    specialize ih rfl d
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  case case t₁ _ _ _ _ _ _ d _ _ ih _ _ =>
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    specialize ih rfl d
    grind only [→ canonical_form_sum, cases Value, → Red.case (t₁ := t₁),
      → Red.case_inl, → Red.case_inr]
