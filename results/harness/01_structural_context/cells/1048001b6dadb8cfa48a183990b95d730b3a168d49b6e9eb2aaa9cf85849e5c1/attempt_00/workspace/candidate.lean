lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simp at mem
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    cases ih_l rfl l with
    | inl val_l =>
        cases ih_r rfl r with
        | inl val_r =>
            obtain ⟨σ, t₁, rfl⟩ := l.canonical_form_abs val_l
            exact Or.inr ⟨t₁ ^ᵗᵗ t₂, Term.Red.abs l.wf.2.1 val_r⟩
        | inr red_r =>
            obtain ⟨t₂', h⟩ := red_r
            exact Or.inr ⟨t₁.app t₂', Term.Red.appᵣ val_l h⟩
    | inr red_l =>
        obtain ⟨t₁', h⟩ := red_l
        exact Or.inr ⟨t₁'.app t₂, Term.Red.appₗ r.wf.2.1 h⟩
  case tapp σ' der sub ih =>
    have hσ : σ'.LC := sub.wf.2.1.lc
    cases ih rfl der with
    | inl val =>
        obtain ⟨σ, t', rfl⟩ := der.canonical_form_tabs val
        exact Or.inr ⟨t' ^ᵗᵞ σ', Term.Red.tabs der.wf.2.1 hσ⟩
    | inr red =>
        obtain ⟨t', h⟩ := red
        exact Or.inr ⟨.tapp t' σ', Term.Red.tapp hσ h⟩
  case let' t₁ σ t₂ τ L der hbody ih ihbody =>
    have hb : t₂.body := ⟨L, fun x hx => (hbody x hx).wf.2.1⟩
    cases ih rfl der with
    | inl val => exact Or.inr ⟨t₂ ^ᵗᵗ t₁, Term.Red.let_body val hb⟩
    | inr red =>
        obtain ⟨t₁', h⟩ := red
        exact Or.inr ⟨t₁'.let' t₂, Term.Red.let_bind h hb⟩
  case inl der _ ih =>
    cases ih rfl der with
    | inl val => exact Or.inl (Term.Value.inl val)
    | inr red =>
        obtain ⟨t', h⟩ := red
        exact Or.inr ⟨.inl t', Term.Red.inl h⟩
  case inr der _ ih =>
    cases ih rfl der with
    | inl val => exact Or.inl (Term.Value.inr val)
    | inr red =>
        obtain ⟨t', h⟩ := red
        exact Or.inr ⟨.inr t', Term.Red.inr h⟩
  case case t₁ σ τ t₂ δ t₃ L der h₂ h₃ ih _ _ =>
    have hb₂ : t₂.body := ⟨L, fun x hx => (h₂ x hx).wf.2.1⟩
    have hb₃ : t₃.body := ⟨L, fun x hx => (h₃ x hx).wf.2.1⟩
    cases ih rfl der with
    | inl val =>
        obtain ⟨u, hu | hu⟩ := der.canonical_form_sum val
        · subst t₁
          cases val with
          | inl vu => exact Or.inr ⟨t₂ ^ᵗᵗ u, Term.Red.case_inl vu hb₂ hb₃⟩
        · subst t₁
          cases val with
          | inr vu => exact Or.inr ⟨t₃ ^ᵗᵗ u, Term.Red.case_inr vu hb₂ hb₃⟩
    | inr red =>
        obtain ⟨t₁', h⟩ := red
        exact Or.inr ⟨t₁'.case t₂ t₃, Term.Red.case h hb₂ hb₃⟩
  case sub => grind
  case abs σ _ τ L _ _ =>
    apply Or.inl
    constructor
    apply Term.LC.abs L
    · grind only [→ wf, cases Term.LC]
    · grind only [→ wf]
  case tabs L _ _ =>
    apply Or.inl
    constructor
    apply Term.LC.tabs L
    · grind only [→ wf, cases Term.LC]
    · grind only [→ wf]
