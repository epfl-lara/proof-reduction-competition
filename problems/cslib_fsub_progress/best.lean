-- Warm-up problem: Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress
-- Variant: best; primary Lean version: v4.33.0-rc2
-- Target starts at the TARGET DECLARATION marker below.
-- Source context: Cslib/Languages/LambdaCalculus/LocallyNameless/Fsub/Safety.lean
-- Proof provenance and scores: ../manifest.json

/-
Copyright (c) 2025 Chris Henson. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Chris Henson
-/

module

public import Cslib.Languages.LambdaCalculus.LocallyNameless.Fsub.Typing

-- Match the local evaluator elaboration settings; no heartbeat measurement here.
set_option maxHeartbeats 0
set_option Elab.async false

/-! # λ-calculus

The λ-calculus with polymorphism and subtyping, with a locally nameless representation of syntax.
This file proves type safety.

## References

* [A. Chargueraud, *The Locally Nameless Representation*][Chargueraud2012]
* See also <https://www.cis.upenn.edu/~plclub/popl08-tutorial/code/>, from which
  this is adapted

-/

public section

namespace Cslib

variable {Var : Type*} [HasFresh Var] [DecidableEq Var]

namespace LambdaCalculus.LocallyNameless.Fsub

open Context List Env.Wf Term Ty

variable {t : Term Var}

/-- Any reduction step preserves typing. -/
lemma Typing.preservation (der : Typing Γ t τ) (step : t ⭢βᵛ t') : Typing Γ t' τ := by
  induction der generalizing t'
  case app Γ _ σ τ _ _ _ _ _ =>
    cases step
    case appₗ | appᵣ => grind
    case abs der _ _ =>
      have sub : Sub Γ (σ.arrow τ) (σ.arrow τ) := by grind [Sub.refl]
      have ⟨_, _, ⟨_, _⟩⟩ := der.abs_inv sub
      grind [fresh_exists <| free_union [fvTm] Var, openTm_substTm_intro, subst_tm, Sub.weaken]
  case tapp Γ _ σ τ σ' _ _ _ =>
    cases step
    case tabs der _ _ =>
      have sub : Sub Γ (σ.all τ) (σ.all τ) := by grind [Sub.refl]
      have ⟨_, _, ⟨_, _⟩⟩ := der.tabs_inv sub
      have ⟨X, mem⟩ := fresh_exists <| free_union [Ty.fv, fvTy] Var
      simp at mem
      have : Γ = (Context.mapVal (·[X := σ']) []) ++ Γ := by grind
      rw [openTy_substTy_intro (X := X), open_subst_intro (X := X)] <;> grind [subst_ty]
    case tapp => grind
  case let' Γ _ _ _ _ L der _ ih₁ _ =>
    cases step
    case let_bind red₁ _ => apply Typing.let' L (ih₁ red₁); grind
    case let_body =>
      grind [fresh_exists <| free_union [fvTm] Var, openTm_substTm_intro, subst_tm]
  case case Γ _ σ τ _ _ _ L _ _ _ ih₁ _ _ =>
    have sub : Sub Γ (σ.sum τ) (σ.sum τ) := by grind [Sub.refl]
    have : Γ = [] ++ Γ := by rfl
    cases step
    case «case» red₁ _ _ => apply Typing.case L (ih₁ red₁) <;> grind
    case case_inl der _ _ =>
      have ⟨_, ⟨_, _⟩⟩ := der.inl_inv sub
      grind [fresh_exists <| free_union [fvTm] Var, openTm_substTm_intro, subst_tm]
    case case_inr der _ _ =>
      have ⟨_, ⟨_, _⟩⟩ := der.inr_inv sub
      grind [fresh_exists <| free_union [fvTm] Var, openTm_substTm_intro, subst_tm]
  all_goals grind [cases Red]

set_option linter.tacticAnalysis.verifyGrindOnly false in
/-- Any typable term either has a reduction step or is a value. -/

-- TARGET DECLARATION BEGIN: Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress
lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var => simp_all
  case abs | tabs =>
    left
    constructor
    exact lc
  case sub => grind only
  case inl | inr =>
    cases lc
    grind only [Value.inl, Value.inr, → Red.inl, → Red.inr]
  all_goals
    right
    try simp only [body_let, body_case] at lc
    cases lc
    grind (gen := 2) only [→ canonical_form_abs, → canonical_form_tabs,
      → canonical_form_sum, cases Value, → Red.abs, → Red.appₗ, → Red.appᵣ,
      → Red.tabs, → Red.tapp, → Red.let_bind,
      → Red.let_body, → Red.case, → Red.case_inl, → Red.case_inr]

-- TARGET DECLARATION END: Cslib.LambdaCalculus.LocallyNameless.Fsub.Typing.progress


end LambdaCalculus.LocallyNameless.Fsub

end Cslib
