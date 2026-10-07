lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => cases mem
  case sub ih => exact ih rfl
  case abs L h _ => left; exact .abs (Typing.abs L h).wf.2.1
  case tabs L h _ => left; exact .tabs (Typing.tabs L h).wf.2.1
  case inl ih | inr ih =>
    obtain (val | ⟨_, h⟩) := ih rfl
    · left; constructor; exact val
    · right; constructor; constructor; exact h
  case app l r ih_l ih_r =>
    right
    obtain (val | ⟨_, h⟩) := ih_l rfl
    · obtain (val₂ | ⟨_, h⟩) := ih_r rfl
      · obtain ⟨_, u, rfl⟩ := l.canonical_form_abs val
        exact ⟨_, .abs val.lc val₂⟩
      · exact ⟨_, .appᵣ val h⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
  case tapp der sub ih =>
    right
    have w := (Sub.wf _ _ _ sub).2.1.lc
    obtain (val | ⟨_, h⟩) := ih rfl
    · obtain ⟨_, u, rfl⟩ := der.canonical_form_tabs val
      exact ⟨_, .tabs val.lc w⟩
    · exact ⟨_, .tapp w h⟩
  case let' L der h ih _ =>
    right
    have B := (Term.body_let.1 (Typing.let' L der h).wf.2.1).2
    obtain (val | ⟨_, h₂⟩) := ih rfl
    · exact ⟨_, .let_body val B⟩
    · exact ⟨_, .let_bind h₂ B⟩
  case case L der h₂ h₃ ih _ _ =>
    right
    have b := (Term.body_case.1 (Typing.case L der h₂ h₃).wf.2.1).2
    obtain (val | ⟨_, h⟩) := ih rfl
    · obtain ⟨u, rfl | rfl⟩ := der.canonical_form_sum val
      · exact ⟨_, .case_inl (by cases val; assumption) b.1 b.2⟩
      · exact ⟨_, .case_inr (by cases val; assumption) b.1 b.2⟩
    · exact ⟨_, .case h b.1 b.2⟩