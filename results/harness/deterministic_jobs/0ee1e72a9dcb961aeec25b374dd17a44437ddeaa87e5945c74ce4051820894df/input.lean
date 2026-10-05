lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l.wf.2.1 with v | ⟨u, h⟩
    · rcases ih_r rfl r.wf.2.1 with w | ⟨u, h⟩
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs v
        exact ⟨_, Red.abs v.lc w⟩
      · exact ⟨_, Red.appᵣ v h⟩
    · exact ⟨_, Red.appₗ r.wf.2.1 h⟩
  case tapp der sub ih =>
    right
    cases lc with
    | tapp lc ty =>
      rcases ih rfl lc with v | ⟨u, h⟩
      · obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs v
        exact ⟨_, Red.tabs v.lc ty⟩
      · exact ⟨_, Red.tapp ty h⟩
  case let' der _ ih _ =>
    obtain ⟨lc, body⟩ := body_let.mp lc
    right
    rcases ih rfl lc with v | ⟨u, h⟩
    · exact ⟨_, Red.let_body v body⟩
    · exact ⟨_, Red.let_bind h body⟩
  case case der _ _ ih _ _ =>
    obtain ⟨lc, b, c⟩ := body_case.mp lc
    right
    rcases ih rfl lc with v | ⟨u, h⟩
    · obtain ⟨u, h | h⟩ := der.canonical_form_sum v
      · subst h; cases v with | inl v => exact ⟨_, Red.case_inl v b c⟩
      · subst h; cases v with | inr v => exact ⟨_, Red.case_inr v b c⟩
    · exact ⟨_, Red.case h b c⟩
  all_goals grind [→ Red.inl, → Red.inr]