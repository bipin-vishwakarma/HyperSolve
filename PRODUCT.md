# HyperSolve

## Platform
Native Windows desktop, built with Python and PyQt6.

## Purpose
The Windows app manages independent quiz-tab agents in everyday Chrome/Edge through a companion extension and native bridge. Supported quizzes are detected automatically; each quiz requires approval before scanning, sending questions to AI, or selecting answers. The dedicated CDP Chrome workspace and screenshot assistant remain separate workflows.

## Current brief
Make the tool a complete Windows application: improve UI and UX, replace the icon, repair the installer, and prepare tested updates for GitHub.

## Constraints
Keep existing user profiles and credentials private and intact. An installed build must not depend on the source checkout or a separately installed Python. Connection status must reflect observation, and controls must perform their labelled action. Do not claim accuracy or capture invisibility without evidence.

## Open decisions
Audience beyond the current user is unconfirmed. The user approved a light workspace with a dark sidebar and explicitly rejected the first green theme as repetitive. The replacement uses an ink/cobalt identity and a tab/check icon. This is project direction, not a cross-project preference.

## Workspace and automation
The companion saves a local window tab/pin snapshot and restores it into a new window. Detection starts automatically, with confirmation per quiz. Each tab has its own controls; API requests can run in parallel while browser AI conversations queue per provider. The manager shows observed counts/states. The dedicated workspace retains its explicit Start/Watch workflow and separate snapshot.
