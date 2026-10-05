lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simp at mem
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub der _ ih => exact ih rfl der.wf.2.1
  case app l r il ir =>
    right
    rcases il rfl l.wf.2.1 with vl | ⟨u, hr⟩
    · have := ir rfl r.wf.2.1
      grind only [→ canonical_form_abs, → Value.lc, → Red.abs, → Red.appᵣ vl]
    · exact ⟨_, Red.appₗ r.wf.2.1 hr⟩
  case tapp der sub ih =>
    have := ih rfl der.wf.2.1
    grind only [→ Sub.wf, → Ty.Wf.lc, → Value.lc, → canonical_form_tabs,
      → Red.tabs, → Red.tapp]
  case let' der _ ih _ =>
    have := ih rfl der.wf.2.1
    have := (body_let.mp lc).2
    grind only [→ Red.let_body, → Red.let_bind]
  case inl der _ ih | inr der _ ih =>
    have := ih rfl der.wf.2.1
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  case case der _ _ ih _ _ =>
    have := ih rfl der.wf.2.1
    obtain ⟨_, b₂, b₃⟩ := body_case.mp lc
    grind only [→ canonical_form_sum, cases Value,
      → (Red.case · b₂ b₃), → (Red.case_inl · b₂ b₃), → (Red.case_inr · b₂ b₃)]
