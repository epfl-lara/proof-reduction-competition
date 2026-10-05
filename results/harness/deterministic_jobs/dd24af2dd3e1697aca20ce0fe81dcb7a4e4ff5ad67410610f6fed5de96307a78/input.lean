lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    cases ih_l rfl l with
    | inl val_l =>
        cases ih_r rfl r with
        | inl val_r =>
            obtain ⟨σ, u, h⟩ := l.canonical_form_abs val_l
            refine ⟨u ^ᵗᵗ t₂, ?_⟩
            rw []
            grind
        | inr red_r =>
            obtain ⟨t₂', red⟩ := red_r
            exact ⟨t₁.app t₂', Red.appᵣ val_l red⟩
    | inr red_l =>
        obtain ⟨t₁', red⟩ := red_l
        exact ⟨t₁'.app t₂, Red.appₗ r.wf.2.1 red⟩
  case tapp σ' d sub ih =>
    have lcσ : σ'.LC := (sub.wf [] σ' _).2.1.lc
    cases ih rfl d with
    | inl val =>
        obtain ⟨δ, u, h⟩ := d.canonical_form_tabs val
        exact Or.inr ⟨u ^ᵗᵞ σ', by rw [h]; exact Red.tabs (h ▸ d.wf.2.1) lcσ⟩
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.tapp u σ', Red.tapp lcσ step⟩
  case let' t₁ σ t₂ τ L der h ih _ =>
    have hb : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
    cases ih rfl der with
    | inl val => exact Or.inr ⟨t₂ ^ᵗᵗ t₁, Red.let_body val hb⟩
    | inr red =>
        obtain ⟨t₁', step⟩ := red
        exact Or.inr ⟨t₁'.let' t₂, Red.let_bind step hb⟩
  case inl der _ ih =>
    cases ih rfl der with
    | inl val => grind
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.inl u, Red.inl step⟩
  case inr der _ ih =>
    cases ih rfl der with
    | inl val => grind
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.inr u, Red.inr step⟩
  case case t₁ σ τ t₂ δ t₃ L der h₂ h₃ ih _ _ =>
    have hb₂ : t₂.body := ⟨L, fun x hx => (h₂ x hx).wf.2.1⟩
    have hb₃ : t₃.body := ⟨L, fun x hx => (h₃ x hx).wf.2.1⟩
    cases ih rfl der with
    | inl val =>
        obtain ⟨u, h | h⟩ := der.canonical_form_sum val
        · subst t₁
          cases val with
          | inl vu => exact Or.inr ⟨t₂ ^ᵗᵗ u, Red.case_inl vu hb₂ hb₃⟩
        · subst t₁
          cases val with
          | inr vu => exact Or.inr ⟨t₃ ^ᵗᵗ u, Red.case_inr vu hb₂ hb₃⟩
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.case u t₂ t₃, Red.case step hb₂ hb₃⟩
  case sub der sub ih => exact ih rfl der
  case abs σ body τ L h ih =>
    grind
  case tabs L h ih =>
    grind