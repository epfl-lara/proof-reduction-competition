lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => simp at mem
  case abs L d _ => exact .inl (.abs (Typing.abs L d).wf.2.1)
  case tabs L d _ => exact .inl (.tabs (Typing.tabs L d).wf.2.1)
  case sub ih => exact ih rfl
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl with vl | ⟨s, h⟩
    · rcases ih_r rfl with vr | ⟨s, h⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl h⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
  case tapp d sub ih =>
    have hs := (Sub.wf _ _ _ sub).2.1.lc
    right
    rcases ih rfl with v | ⟨s, h⟩
    · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc hs⟩
    · exact ⟨_, .tapp hs h⟩
  case let' t₁ σ t₂ τ L d h ih _ =>
    have hb : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
    right
    rcases ih rfl with v | ⟨s, hr⟩
    · exact ⟨_, .let_body v hb⟩
    · exact ⟨_, .let_bind hr hb⟩
  case inl _ _ ih =>
    rcases ih rfl with v | ⟨s, h⟩
    · exact .inl (.inl v)
    · exact .inr ⟨_, .inl h⟩
  case inr _ _ ih =>
    rcases ih rfl with v | ⟨s, h⟩
    · exact .inl (.inr v)
    · exact .inr ⟨_, .inr h⟩
  case case t₁ _ _ t₂ _ t₃ L d h₂ h₃ ih _ _ =>
    have b₂ : t₂.body := ⟨L, fun x hx => (h₂ x hx).wf.2.1⟩
    have b₃ : t₃.body := ⟨L, fun x hx => (h₃ x hx).wf.2.1⟩
    right
    rcases ih rfl with v | ⟨s, h⟩
    · obtain ⟨s, e | e⟩ := d.canonical_form_sum v
      · subst e
        cases v with
        | inl v => exact ⟨_, .case_inl v b₂ b₃⟩
      · subst e
        cases v with
        | inr v => exact ⟨_, .case_inr v b₂ b₃⟩
    · exact ⟨_, .case h b₂ b₃⟩
