lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var => simp_all
  case abs | tabs =>
    left
    constructor
    exact lc
  case sub => grind only
  case inl | inr =>
    cases lc
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  all_goals
    right
    try simp only [body_let, body_case] at lc
    cases lc
    grind (gen := 2) only [→ canonical_form_abs, → canonical_form_tabs,
      → canonical_form_sum, cases Value, → Red.abs, → Red.appₗ, → Red.appᵣ,
      → Red.tabs, → Red.tapp, → Red.let_bind,
      → Red.let_body, → Red.case, → Red.case_inl, → Red.case_inr]
