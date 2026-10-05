lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs L h _ => exact .inl (.abs (Typing.abs L h).wf.2.1)
  case tabs L h _ => exact .inl (.tabs (Typing.tabs L h).wf.2.1)
  case sub ih => exact ih rfl
  case' app l r ih_l ih_r =>
    have := ih_l rfl
    have := ih_r rfl
    have := l.wf.2.1
    have := r.wf.2.1
  case' tapp der sub ih =>
    have := ih rfl
    have := der.wf.2.1
    have := (sub.wf _ _ _).2.1.lc
  case' let' t₁ σ t₂ τ L der h ih _ =>
    have := ih rfl
    have body : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
  case' inl ih | inr ih => have := ih rfl
  case' case t₁ _ _ t₂ _ t₃ L der h₂ h₃ ih _ _ =>
    have b₂ : t₂.body := ⟨L, fun x hx => (h₂ x hx).wf.2.1⟩
    have b₃ : t₃.body := ⟨L, fun x hx => (h₃ x hx).wf.2.1⟩
    rcases ih rfl with val | ⟨_, red⟩
    case' inl => obtain ⟨_, h | h⟩ := der.canonical_form_sum val <;> subst h <;> cases val
  all_goals aesop (add 50% constructors [Value, Red]) (add safe forward [canonical_form_abs, canonical_form_tabs])