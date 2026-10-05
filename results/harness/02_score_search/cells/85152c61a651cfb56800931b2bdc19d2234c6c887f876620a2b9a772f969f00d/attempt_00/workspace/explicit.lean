lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs =>
    left
    constructor
    exact der'.wf.2.1
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l with vl | ⟨_, hl⟩
    · rcases ih_r rfl r with vr | ⟨_, hr⟩
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl hr⟩
    · exact ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp d s ih =>
    right
    have lc := (Sub.wf _ _ _ s).2.1.lc
    rcases ih rfl d with v | ⟨_, h⟩
    · obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc lc⟩
    · exact ⟨_, .tapp lc h⟩
  case let' d _ ih _ =>
    right
    have b := (body_let.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨_, h⟩
    · exact ⟨_, .let_body v b⟩
    · exact ⟨_, .let_bind h b⟩
  case inl d _ ih =>
    rcases ih rfl d with v | ⟨_, h⟩
    · exact .inl (.inl v)
    · exact .inr ⟨_, .inl h⟩
  case inr d _ ih =>
    rcases ih rfl d with v | ⟨_, h⟩
    · exact .inl (.inr v)
    · exact .inr ⟨_, .inr h⟩
  case case d _ _ ih _ _ =>
    right
    have b := (body_case.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨_, h⟩
    · obtain ⟨_, h | h⟩ := d.canonical_form_sum v
      · subst h
        cases v with | inl v => exact ⟨_, .case_inl v b.1 b.2⟩
      · subst h
        cases v with | inr v => exact ⟨_, .case_inr v b.1 b.2⟩
    · exact ⟨_, .case h b.1 b.2⟩
  case sub d _ ih => exact ih rfl d
