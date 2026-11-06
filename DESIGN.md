---
name: HyperSolve Desktop
description: A native Windows workspace for deliberate browser sessions.
colors:
  primary: '#3759dc'
  primary-hover: '#2945b5'
  focus: '#3759dc'
  status-text: '#3c4f83'
  status-surface: '#e9edfb'
  workspace: '#f3f4f8'
  surface: '#ffffff'
  sidebar: '#191e2e'
  sidebar-text: '#bdc5d9'
  sidebar-hover: '#252c42'
  sidebar-selected: '#313c60'
  text: '#24293b'
  title: '#1d2335'
  muted: '#606b82'
  panel-border: '#dfe3ed'
  control-border: '#c2c9da'
  control-hover: '#eceffa'
  control-border-hover: '#8d9ab8'
  control-pressed: '#e1e6f5'
  disabled: '#e7eaf1'
  disabled-border: '#d8deea'
  disabled-text: '#6c7589'
  progress-track: '#e4e8f3'
  rail-state-text: '#cbd4f3'
  empty-title: '#303b5a'
typography:
  headline:
    fontFamily: Segoe UI
    fontSize: 30px
    fontWeight: 600
  brand:
    fontFamily: Segoe UI
    fontSize: 20px
    fontWeight: 600
  title:
    fontFamily: Segoe UI
    fontSize: 16px
    fontWeight: 600
  body:
    fontFamily: Segoe UI
    fontSize: 14px
  label:
    fontFamily: Segoe UI
    fontSize: 14px
    fontWeight: 600
  diagnostic:
    fontFamily: Cascadia Mono, Consolas
    fontSize: 12px
  empty-title:
    fontFamily: Segoe UI
    fontSize: 21px
    fontWeight: 600
  setup-detail:
    fontFamily: Segoe UI
    fontSize: 12px
rounded:
  progress: 2px
  checkbox: 3px
  status: 4px
  control: 5px
  panel: 8px
  workbench: 9px
spacing:
  small: 7px
  control-gap: 10px
  panel-gap: 12px
  page-gap: 18px
  column-gap: 24px
components:
  button-primary:
    backgroundColor: '{colors.primary}'
    textColor: '{colors.surface}'
    rounded: '{rounded.control}'
    padding: 9px 15px
    typography: '{typography.label}'
  button-secondary:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    rounded: '{rounded.control}'
    padding: 9px 15px
  tab-selector:
    backgroundColor: '{colors.surface}'
    textColor: '{colors.text}'
    rounded: '{rounded.control}'
    padding: 10px
  navigation:
    backgroundColor: '{colors.sidebar}'
    textColor: '{colors.sidebar-text}'
    padding: 12px 13px
    width: 198px
  status:
    backgroundColor: '{colors.status-surface}'
    textColor: '{colors.status-text}'
    rounded: '{rounded.status}'
    padding: 7px 12px
  panel:
    backgroundColor: '{colors.surface}'
    rounded: '{rounded.panel}'
    padding: 20px 22px
  workbench:
    backgroundColor: '{colors.surface}'
    rounded: '{rounded.workbench}'
    padding: 22px 22px 18px
---

# Design System: HyperSolve Desktop

## Overview

**Creative North Star: "Windows Operate"**

The Windows Operate utility is a calm, practical workspace. A light working surface and dark persistent sidebar separate tasks from navigation. Cobalt marks primary actions and observed status; typography and spacing carry the hierarchy.

The application retains the standard Windows titlebar and uses native PyQt6 controls with the Fusion widget style. This document captures the implemented desktop, with dashboard_window.py as the source authority; browser HUD styling is a separate surface.

**Key Characteristics:**
- Light workbench with a persistent ink rail and cobalt actions.
- Results-first workbench, live setup guidance, and an expandable activity log.
- Flat panels, cobalt actions, and standard Windows framing.

## Colors

The single cobalt accent sits within cool neutral surfaces. Frontmatter values are normative; names below describe their use.

### Primary

Cobalt blue (`primary`) identifies Start session and the principal setup or install action. The darker hover shade reinforces interaction. Pale blue status surfaces and text distinguish status labels without suggesting verified accuracy. The focus token marks keyboard interaction.

### Neutral

Cool paper (`workspace`) forms the application background; white (`surface`) defines panels and controls. Slate (`sidebar`) anchors navigation, with lighter slate hover and selected states. Dark ink (`text`, `title`) supports content, while `muted` supports explanatory copy. Panel and control borders establish boundaries. Disabled controls use separate surface, border, and text tokens.

## Typography

Segoe UI is the interface family. Page headings use the headline role, branding the brand role, and panel titles the title role. Body text and controls share the body scale; button labels are semibold. Diagnostics use Cascadia Mono with Consolas fallback. No custom line-height or letter spacing is defined by the desktop stylesheet.

## Layout

The standard OS titlebar surrounds one desktop window. Its initial client size is 1160 by 780, with a minimum of 860 by 620; saved geometry is restored. A persistent 198px sidebar contains Workspace, Connections, and Settings. Pages scroll rather than collapsing the rail into mobile navigation.

Page margins are 32px horizontally, 28px above, and 26px below, with 18px gaps. Panels use 22px horizontal and 20px vertical padding and 12px internal gaps. The sidebar uses 14px horizontal, 28px top, and 20px bottom padding. The results workbench sits beside a 218px live setup column, separated by a 24px gap. Below a window width of 1040px, the setup column is hidden and its next-step action moves into the workbench toolbar. The rail stays visible. The activity log is collapsed by default and opens to 110px height. There are no animated layout transitions.

## Elevation & Depth

The desktop is flat: no application-defined shadows. White panels, thin cool borders, and the darker navigation rail convey separation. Windows owns the external window frame and its platform decoration.

## Shapes

Panels have gently rounded corners; controls use a slightly tighter curve. Status labels, checkbox indicators, and progress tracks use the smaller radii in frontmatter. Borders are normally one pixel; focused controls use a two-pixel cobalt border. The progress bar is at most four pixels high.

## Components

The browser overlay uses an ink header and white cobalt-accented panel, 360px maximum width, 12px corners and an offset shadow. Keep Pause/Resume and Stop in a sticky footer; collapse retains those controls. Selected answers and activity are bounded scroll regions, and a dragged panel reclamps after content or viewport changes. Use the same 13px Segoe UI text and 12px labels as implemented in hud/assets/styles.css.

Session controls include a mode selector for selected-tab runs and explicitly started automatic detection. Connections includes a Saved workspace panel with Save/Restore actions, progress, and local snapshot status. Use existing combo-box and button styles; no new colour or typography tokens.

### Buttons

Primary buttons use cobalt with white text and a darker hover. Secondary buttons use white, a cool border, a pale hover, and a slightly darker pressed state. Disabled buttons use the shared disabled palette. All use the control radius and semibold labels. Keyboard focus is outlined in cobalt; the current stylesheet changes states immediately.

### Cards / Containers

White bordered panels group a single task. They use the panel radius and padding defined above, with controls retaining their own surfaces. They have no hover elevation.

### Inputs / Fields

The browser selector is a native combo box with a white surface, control border and radius, 10px padding, and a 20px minimum content height. The checkbox uses a 16px indicator, 10px label gap, and an inline check image when selected. The read-only activity log uses the diagnostic font, panel border, and 10px padding.

### Navigation

The persistent sidebar uses left-aligned labels with navigation icons. A browser connection indicator sits at its foot. Hover lightens the rail; the checked item uses a stronger slate selection. Navigation does not collapse at the minimum window size. The tray menu uses white surfaces and a pale blue selection.

### Status and progress

A pale blue label carries literal session status. A thin cobalt progress track reflects selected question counts. These are informative controls, not claims that answers are correct.

### Results workbench

The white results workbench keeps source selection, session actions, progress, and answers together. Its inset spacing is 22px on top and sides and 18px below. A thin divider separates controls from results. The empty state uses an overlapping browser-tab and checkmark illustration, a semibold title, and centered explanatory copy. The application icon follows the tab/check identity. The log disclosure reveals diagnostic activity on demand.

## Do's and Don'ts

### Do:
- Do retain the ink-and-cobalt workbench, dark persistent sidebar, and standard OS titlebar.
- Do use Segoe UI for interface text and monospace only for diagnostic activity.
- Do retain visible keyboard focus and readable disabled states.
- Do describe connection and session states using observed facts.

### Don't:
- Keep native manager motion restrained. The user approved a glass browser panel: translucent white/cobalt materials, 180ms phase transitions, and reduced-motion support. Its compact/expanded states keep action controls reachable.
- Don't replace native window controls with a custom titlebar.
- Don't imply that a detected provider tab proves sign-in or answer accuracy.
