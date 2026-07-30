# HTML Planner Design System

## Direction

Encase, tuned for a developer workspace. The interface uses hard containment, binary contrast, and a restrained lime signal for state and focus. It should feel like a reliable command center rather than a decorative SaaS dashboard.

## Color

- Ink: `#0A0A0A`
- Paper: `#F4F4F1`
- Surface: `#FFFFFF`
- Panel: `#E8E8E4`
- Muted text: `#5F5F5A`
- Accent: `#D8FF3E`
- Warning: `#C99100`
- Danger: `#B42318`

Dark mode swaps the neutral surfaces to `#11110F`, `#1C1C19`, and `#262622`, keeps the accent at `#D8FF3E`, and raises muted text to `#C0C0B8` for readable contrast.

Use the accent only for focus, pinned or published state, and small readiness signals. Use black and white for structure.

## Typography

Use a single system sans stack for all product UI: Arial, Helvetica Neue, sans-serif. Use SFMono-Regular, Consolas, or Liberation Mono for IDs, commands, and timestamps. Structural labels are uppercase and bold with modest tracking. Body copy stays sentence case.

## Shape And Containment

- Borders: 2px black for primary containers and controls.
- Radius: 6px to 10px for controls and panels.
- Shadows: only hard offset shadows on focal surfaces, never soft card decoration.
- Buttons: verb plus object, with filled black for the primary action.

## Layout

The dashboard uses a top command bar, a compact workspace rail on desktop, and a dense plan inventory in the main column. Plan rows keep status and actions in the same scan path. At mobile widths, the rail collapses and rows stack without hiding controls.

## Interaction

Loading uses skeleton rows. Errors stay inline with a retry action. Empty states teach the CLI command. Preview uses the native dialog element. All actions expose focus states, work from the keyboard, and honor reduced-motion preferences.

The theme toggle appears in the landing page header and dashboard command bar. It follows the system preference on first visit, persists an explicit choice in `localStorage`, and updates the browser theme color.
