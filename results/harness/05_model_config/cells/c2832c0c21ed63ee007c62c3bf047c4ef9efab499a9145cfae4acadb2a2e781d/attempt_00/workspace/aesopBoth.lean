lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub ih => exact ih rfl lc
  case app l r ih_l ih_r =>
    have := ih_l rfl l.wf.2.1
    have := ih_r rfl r.wf.2.1
    right
    aesop (add safe forward [canonical_form_abs, wf, Value.lc]) (add 50% constructors Red)
  case tapp d s ih =>
    have := ih rfl d.wf.2.1
    have := s.wf.2.1.lc
    grind only [→ canonical_form_tabs, → Value.lc, → Red.tapp, → Red.tabs]
  case let' d _ ih _ =>
    have h := body_let.mp lc
    have := ih rfl d.wf.2.1
    grind only [→ Red.let_body, → Red.let_bind]
  case inl d _ ih | inr d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨_, v⟩ <;> [left; right] <;>
      repeat' first | assumption | constructor
  case case d _ _ ih _ _ =>
    have h := body_case.mp lc
    have := ih rfl d.wf.2.1
    right
    aesop (add safe forward canonical_form_sum) (add safe cases Value)
      (add 50% constructors Red)
