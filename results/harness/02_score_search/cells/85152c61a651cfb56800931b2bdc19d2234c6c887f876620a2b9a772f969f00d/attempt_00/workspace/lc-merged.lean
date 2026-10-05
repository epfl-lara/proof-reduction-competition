lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs =>
    left
    constructor
    exact lc
  case app | tapp | inl | inr =>
    cases lc
    grind (gen := 2) only [→ canonical_form_abs, → canonical_form_tabs,
      Value.inl, Value.inr, → Red.abs, → Red.appₗ, → Red.appᵣ,
      → Red.tabs, → Red.tapp, → Red.inl, → Red.inr]
  case let' =>
    grind only [body_let, → Red.let_bind, → Red.let_body]
  case case =>
    grind (gen := 2) only [body_case, → canonical_form_sum, cases Value,
      → Red.case, → Red.case_inl, → Red.case_inr]
  case sub d _ ih => exact ih rfl lc
