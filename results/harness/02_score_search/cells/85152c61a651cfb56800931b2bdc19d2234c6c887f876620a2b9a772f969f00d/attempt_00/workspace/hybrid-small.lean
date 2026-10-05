lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs =>
    left
    constructor
    exact der'.wf.2.1
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l with vl | ⟨_, hl⟩
    · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
      grind only [→ Value.lc, → Red.abs, → Red.appᵣ]
    · exact ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp =>
    grind only [→ canonical_form_tabs, → Sub.wf, → Ty.Wf.lc, → Value.lc, → Red.tabs, → Red.tapp]
  case let' =>
    grind only [→ wf, body_let, → Red.let_bind, → Red.let_body]
  case inl | inr =>
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  case case d _ _ ih _ _ =>
    right
    have b := (body_case.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨_, h⟩
    · have := d.canonical_form_sum v
      grind only [cases Value, → Red.case_inl, → Red.case_inr]
    · exact ⟨_, .case h b.1 b.2⟩
  case sub d _ ih => exact ih rfl d
