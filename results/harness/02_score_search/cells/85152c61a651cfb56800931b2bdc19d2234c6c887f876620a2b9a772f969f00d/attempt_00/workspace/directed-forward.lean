lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs =>
    left
    constructor
    exact der'.wf.2.1
  case app =>
    grind only [→ canonical_form_abs, → wf, → Value.lc, → Red.abs, → Red.appₗ, → Red.appᵣ]
  case tapp =>
    grind only [→ canonical_form_tabs, → Sub.wf, → Ty.Wf.lc, → Value.lc, → Red.tabs, → Red.tapp]
  case let' =>
    grind only [→ wf, body_let, → Red.let_bind, → Red.let_body]
  case inl | inr =>
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  case case =>
    grind only [→ wf, body_case, → canonical_form_sum, cases Value,
      → Red.case, → Red.case_inl, → Red.case_inr]
  case sub d _ ih => exact ih rfl d
