lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => simp at mem
  case app l r il ir =>
    right
    rcases il rfl l with vl | ⟨u, hr⟩
    · have := ir rfl r
      grind only [l.canonical_form_abs vl, vl.lc, → Red.abs, → Red.appᵣ vl]
    · exact ⟨_, Red.appₗ r.wf.2.1 hr⟩
  case tapp =>
    grind only [→ Sub.wf, → Ty.Wf.lc, → Value.lc, → canonical_form_tabs,
      → Red.tabs, → Red.tapp]
  case let' =>
    have := (body_let.mp der'.wf.2.1).2
    grind only [→ Red.let_body, → Red.let_bind]
  case case =>
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    grind only [→ canonical_form_sum, cases Value,
      → (Red.case · b₂ b₃), → (Red.case_inl · b₂ b₃), → (Red.case_inr · b₂ b₃)]
  all_goals grind only [→ wf, intro Value,
    → Red.inl, → Red.inr]
