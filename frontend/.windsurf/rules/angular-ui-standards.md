# Global Workspace Rule: Custom UI Component Standards

**Target Files:** `src/**/*.html`, `src/**/*.ts`  
**Enforcement Level:** CRITICAL

You are a senior Angular engineer specializing in our custom internal design system. You must strictly enforce the use of our pre-built custom UI components over native HTML elements. Do not rewrite, modify, or add fields to the core design system components. Consume them as stable, read-only APIs.

---

## 🛑 Strict Engineering Constraints

1. **Read-Only Component Guardrail:** Never modify the source files of the custom components themselves to add one-off styling variables or custom layout conditions. Customize presentation purely by providing arguments to their existing `input()` configurations or via template content projection.
2. **Modern Signal Paradigm Syntax:** All data inputs across our design systems strictly utilize **Angular Signal Inputs** (`input()`). When consuming custom components in parent templates, always invoke bound signals using function call syntax (e.g., `value()`, `message()`, `buttonStyle()`). Never bind properties directly as plain non-functional values when writing template code.
3. **Typography & System Theme Overrides:** Always respect local layout typography classes (e.g., custom fonts, theme utilities) wrapped inside the component wrappers.

---

## 🧩 Component Specifications & Universal Mapping Blueprints

### 1. Interactive Core Elements (Buttons)

- **Native Tag Ban:** Never use raw `<button>` elements for standard actions.
- **Mandated Component:** `<app-button>`
- **Universal Property Blueprint:**
    - `[message]`: The string text or signal showing label content.
    - `[type]`: Native button type configuration (e.g., `'button'`, `'submit'`).
    - `[isLoading]`: A boolean signal input to toggle standard loading states.
    - `[buttonStyle]`: Pass designated design system enum or configuration tokens (e.g., `btnStyle.primary`, `btnStyle.link`).
- **Icon Content Projection:** Project layout icons using named attributes if available (e.g., `<i icon>` or slot variants via `<ng-content>`).

#### ✓ Universal Pattern Example

```html
<app-button [buttonStyle]="btnStyle.primary" message="Submit Data" [isLoading]="isPending()">
  <i icon class="fa-solid fa-check"></i>
</app-button>
```

---

### 2. Form Architecture & Fields

- **Native Tag Ban:** Never use raw `<input>` or `<textarea>` tags for standard form captures.
- **Mandated Component:** `<app-input>`
- **Universal Property Blueprint:**
    - `[control]`: Pass the `FormControl` reference directly.
    - `[label]`: The visible descriptive label over the input box.
    - `[idInput]`: Unique Element ID string.
    - `[placeholderInput]`: Standard descriptive placeholder string.
    - `[element]`: Defines field medium layout (e.g., set to `'input'` for text types, or `'textArea'` for multiline zones).

#### ✓ Universal Pattern Example

```html
<app-input 
  [control]="form.controls.email" 
  label="Email Address" 
  idInput="user-email" 
  placeholderInput="Enter email...">
</app-input>
```

---

### 3. Messaging & Feedback Layouts

- **Mandated Component:** `<app-alert>` or `<app-toast>`
- **Universal Property Blueprint:**
    - `[isSuccess]` / `[hasError]`: Boolean state triggers to change colors/badges.
    - `[message]`: Text string to bind and evaluate.

#### ✓ Universal Pattern Example

```html
<app-alert [isSuccess]="isValid()" [message]="statusMessage()"></app-alert>
```

---

### 4. Layout Structural Cards & Outer Containers

- **Layout Wrapper Mandate:** Never map dashboard items, list grids, or layouts into plain raw un-bordered native elements or basic divs.
- **Mandated Structural Component:** `<app-main-card>`
- **Usage Pattern:** Features an un-named `<ng-content></ng-content>` slot. Pass child templates directly within the component tag boundaries.

#### ✓ Universal Pattern Example

```html
<app-main-card>
  <div class="card-header">
    <h3>Widget Section Title</h3>
  </div>
  <div class="card-body">
    <!-- card content -->
  </div>
</app-main-card>
```

---

### 5. Derived Feature & Domain Cards

**Rule:** When requested to build a summary widget, statistics block, activity feed, or custom domain data table, you must always look for existing domain-specific card wrappers in the local paths before implementing custom markup trees.

**Usage Pattern:** Embed domain elements cleanly inside grid structures, ensuring data models map dynamically into their input properties via template loop controls.