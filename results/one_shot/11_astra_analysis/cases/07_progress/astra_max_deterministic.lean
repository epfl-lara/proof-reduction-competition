lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => cases mem
  case abs => grind
  case tabs => grind
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l with v | ⟨_, h⟩
    · rcases ih_r rfl r with w | ⟨_, h⟩
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs v
        exact ⟨_, .abs v.lc w⟩
      · exact ⟨_, .appᵣ v h⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
  case tapp der sub ih =>
    right
    have lc := (Sub.wf _ _ _ sub).2.1.lc
    rcases ih rfl der with v | ⟨_, h⟩
    · obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs v
      exact ⟨_, .tabs v.lc lc⟩
    · exact ⟨_, .tapp lc h⟩
  case let' der _ ih _ =>
    right
    have b := (body_let.mp der'.wf.2.1).2
    rcases ih rfl der with v | ⟨_, h⟩
    · exact ⟨_, .let_body v b⟩
    · exact ⟨_, .let_bind h b⟩
  case inl der _ ih =>
    rcases ih rfl der with v | ⟨_, h⟩
    · exact .inl (.inl v)
    · exact .inr ⟨_, .inl h⟩
  case inr der _ ih =>
    rcases ih rfl der with v | ⟨_, h⟩
    · exact .inl (.inr v)
    · exact .inr ⟨_, .inr h⟩
  case case der _ _ ih _ _ =>
    right
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    rcases ih rfl der with v | ⟨_, h⟩
    · obtain ⟨_, rfl | rfl⟩ := der.canonical_form_sum v
      · cases v with
        | inl v => exact ⟨_, .case_inl v b₂ b₃⟩
      · cases v with
        | inr v => exact ⟨_, .case_inr v b₂ b₃⟩
    · exact ⟨_, .case h b₂ b₃⟩
  case sub der _ ih => exact ih rfl der
