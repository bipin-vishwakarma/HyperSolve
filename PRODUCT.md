# HyperSolve

## Platform
Native Windows desktop, built with Python and PyQt6.

## Purpose
The existing application connects to a dedicated Chrome profile and routes page questions to browser AI sessions or optional API credentials. The desktop screenshot assistant remains a separate workflow.

## Current brief
Make the tool a complete Windows application: improve UI and UX, replace the icon, repair the installer, and prepare tested updates for GitHub.

## Constraints
Keep existing user profiles and credentials private and intact. An installed build must not depend on the source checkout or a separately installed Python. Connection status must reflect observation, and controls must perform their labelled action. Do not claim accuracy or capture invisibility without evidence.

## Open decisions
Audience beyond the current user is unconfirmed. The user approved a light workspace with a dark sidebar and explicitly rejected the first green theme as repetitive. The replacement uses an ink/cobalt identity and a tab/check icon. This is project direction, not a cross-project preference.

## Workspace and automation
Save one local snapshot of open web tabs and selected source. Restore missing tabs while preserving current ones and the existing Chrome profile. Automation starts only on an explicit Start; Watch mode continues detecting supported quizzes until stopped or a terminal error occurs.
