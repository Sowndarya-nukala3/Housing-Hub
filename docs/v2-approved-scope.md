# Housing Hub 2.0 — approved scope

Tagline: One Home. One Hub. Primary visual reference: user-approved Housing Hub 2.0 Chat Showcase image (lavender miniature 3D home, rounded pastel cards, cute avatars). Five tabs: Home, Tasks, Bills, Calendar, Profile. Floating chat bubble only.

1. Interactive 3D home, room markers, rotation, zoom, accessible fallback.
2. Ready-made household templates; 10 owned hubs, 12 guests each; secure invitation links only.
3. Room, timeline and board chores; manual, rotation and fair assignment; mutual swaps.
4. Rich/grouped push notifications, summaries, quiet hours, quick actions.
5. Bills: Revolut links, verified confirmation only where supported, recipient confirmation, recurring expenses, all splits, receipts, partial payments, budgets, PDF/Excel, settlement recommendations. Grocery expenses only; no standalone groceries.
6. Monthly internal calendar, intelligent scheduling with admin override, holiday mode, conflicts, recurrence, fair reassignment, bill deadlines, history, separate household calendars.
7. Combined profile, three avatar types, 3D customization, optional achievements, light/dark/system/custom pastel accents, advanced admin and privacy controls.
8. Cinematic welcome, email/password, mobile OTP, biometric unlock, skippable tutorial, advanced security.
9. Permanent household group and private messages only; photos, videos, files, polls, GIFs, emojis, reactions, voice notes, interactive chore/bill/event cards. No custom groups or chat tab.

## Security acceptance criteria
Removal revokes all household APIs, media and live connections, clears app caches and notifications, hides hub and chats, preserves other hubs and financial ledger. Rejoining requires a new invitation; message history starts at new membership date. Old invitations must not allow bypass. Administrators cannot read private conversations solely by virtue of role. Previously downloaded files cannot be remotely erased. Test cross-hub access, removed users, stale sessions, rejoining history and concurrent removal. Do not merge until regression and security tests pass.

External dependencies: SMS/email, push, licensed GIF provider, private media storage, 3D assets, supported Revolut verification. No custody of funds.
