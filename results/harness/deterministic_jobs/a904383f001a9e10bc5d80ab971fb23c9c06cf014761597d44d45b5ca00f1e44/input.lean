lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have : Typing Γ t τ := der
  induction der <;> subst eq
  case var => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl l with val_l | ⟨t₁', red_l⟩
    · rcases ih_r rfl r with val_r | ⟨t₂', red_r⟩
      · obtain ⟨σ, u, h⟩ := l.canonical_form_abs val_l
        use u ^ᵗᵗ t₂
        grind
      · exact ⟨t₁.app t₂', Red.appᵣ val_l red_r⟩
    · exact ⟨t₁'.app t₂, Red.appₗ r.wf.2.1 red_l⟩
  case tapp σ' d sub ih =>
    have lcσ : σ'.LC := (sub.wf [] σ' _).2.1.lc
    right
    rcases ih rfl d with val | ⟨u, step⟩
    · obtain ⟨δ, v, h⟩ := d.canonical_form_tabs val
      exact ⟨v ^ᵗᵞ σ', by grind⟩
    · exact ⟨.tapp u σ', Red.tapp lcσ step⟩
  case let' t₁ _ t₂ _ L der h ih _ =>
    have ⟨_, hb⟩ := Term.body_let.mp (Typing.let' L der h).wf.2.1
    right
    rcases ih rfl der with val | ⟨t₁', step⟩
    · exact ⟨t₂ ^ᵗᵗ t₁, Red.let_body val hb⟩
    · exact ⟨t₁'.let' t₂, Red.let_bind step hb⟩
  case inl der _ ih =>
    rcases ih rfl der with val | ⟨u, step⟩
    · grind
    · exact Or.inr ⟨.inl u, Red.inl step⟩
  case inr der _ ih =>
    rcases ih rfl der with val | ⟨u, step⟩
    · grind
    · exact Or.inr ⟨.inr u, Red.inr step⟩
  case case t₁ _ _ t₂ _ t₃ L der h₂ h₃ ih _ _ =>
    have ⟨_, hb₂, hb₃⟩ := Term.body_case.mp (Typing.case L der h₂ h₃).wf.2.1
    right
    rcases ih rfl der with val | ⟨u, step⟩
    · rcases der.canonical_form_sum val with ⟨v, h | h⟩
      · subst t₁
        cases val with
        | inl vv => exact ⟨t₂ ^ᵗᵗ v, Red.case_inl vv hb₂ hb₃⟩
      · subst t₁
        cases val with
        | inr vv => exact ⟨t₃ ^ᵗᵗ v, Red.case_inr vv hb₂ hb₃⟩
    · exact ⟨.case u t₂ t₃, Red.case step hb₂ hb₃⟩
  case sub => grind
  case abs => grind
  case tabs => grind