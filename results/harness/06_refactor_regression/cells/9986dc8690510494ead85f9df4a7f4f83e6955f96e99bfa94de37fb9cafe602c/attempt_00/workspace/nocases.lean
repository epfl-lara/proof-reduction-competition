lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => cases mem
  case app l r il ir =>
    cases il rfl l <;>
      grind only [→ canonical_form_abs, → Red.abs,
        → Red.appᵣ, → Red.appₗ r.wf.2.1]
  case' tapp =>
    cases der'.wf.2.1
  case let' =>
    grind only [(body_let.mp der'.wf.2.1).2, → Red.let_body, → Red.let_bind]
  case case =>
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    grind only [→ canonical_form_sum,
      → (Red.case · b₂ b₃), → (Red.case_inl · b₂ b₃), → (Red.case_inr · b₂ b₃)]
  all_goals grind only [der'.wf.2.1, intro Value,
    → Red.inl, → Red.inr, → canonical_form_tabs, → Red.tabs, → Red.tapp]
