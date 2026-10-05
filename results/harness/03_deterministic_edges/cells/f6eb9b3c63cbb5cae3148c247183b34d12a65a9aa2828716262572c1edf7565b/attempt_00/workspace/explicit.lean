lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs => exact .inl (.abs der'.wf.2.1)
  case tabs => exact .inl (.tabs der'.wf.2.1)
  case sub d _ ih => exact ih rfl d
  case app l r ih_l ih_r =>
    rcases ih_l rfl l with vl | ⟨_, hl⟩
    · rcases ih_r rfl r with vr | ⟨_, hr⟩
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
        exact .inr ⟨_, .abs vl.lc vr⟩
      · exact .inr ⟨_, .appᵣ vl hr⟩
    · exact .inr ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp σ' d _ ih =>
    have lc : σ'.LC := by cases der'.wf.2.1; assumption
    rcases ih rfl d with v | ⟨_, h⟩
    · obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
      exact .inr ⟨_, .tabs v.lc lc⟩
    · exact .inr ⟨_, .tapp lc h⟩
  case let' d _ ih _ =>
    have b := (body_let.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨_, h⟩
    · exact .inr ⟨_, .let_body v b⟩
    · exact .inr ⟨_, .let_bind h b⟩
  case inl d _ ih | inr d _ ih =>
    rcases ih rfl d with v | ⟨_, h⟩
    · exact .inl (by constructor; exact v)
    · exact .inr ⟨_, by constructor; exact h⟩
  case case d _ _ ih _ _ =>
    obtain ⟨_, b, c⟩ := body_case.mp der'.wf.2.1
    rcases ih rfl d with v | ⟨_, h⟩
    · obtain ⟨_, e | e⟩ := d.canonical_form_sum v <;> subst e <;> cases v
      · exact .inr ⟨_, .case_inl ‹_› b c⟩
      · exact .inr ⟨_, .case_inr ‹_› b c⟩
    · exact .inr ⟨_, .case h b c⟩
