lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simp at mem
  case abs => exact .inl (.abs der'.wf.2.1)
  case tabs => exact .inl (.tabs der'.wf.2.1)
  case sub ih => exact ih rfl ‹_›
  case app l r il ir =>
    have := il rfl l
    have := ir rfl r
    grind only [→ wf, → Value.lc, → canonical_form_abs,
      → Red.abs, → Red.appₗ, → Red.appᵣ]
  case tapp der sub ih =>
    have := ih rfl der
    grind only [→ Sub.wf, → Ty.Wf.lc, → Value.lc, → canonical_form_tabs,
      → Red.tabs, → Red.tapp]
  case let' der _ ih _ =>
    have := ih rfl der
    have := (body_let.mp der'.wf.2.1).2
    grind only [→ Red.let_body, → Red.let_bind]
  case inl der _ ih =>
    have := ih rfl der
    grind only [→ Value.inl, → Red.inl]
  case inr der _ ih =>
    have := ih rfl der
    grind only [→ Value.inr, → Red.inr]
  case case der _ _ ih _ _ =>
    have := ih rfl der
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    grind only [→ canonical_form_sum, cases Value,
      → Red.case, → Red.case_inl, → Red.case_inr]
