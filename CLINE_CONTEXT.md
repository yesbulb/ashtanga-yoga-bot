# Project context

This is a Telegram bot for learning Ashtanga yoga asanas.

## Core features
- Two modes: Learning and Testing
- Learning mode:
  - User studies asanas by series (1, 2, 3)
  - Each asana has image, Russian name, Sanskrit name and etymology
  - Buttons: "Запомнил" / "Повторить ещё раз"
  - After 15 asanas: repeat all / repeat only marked / back to menu

- Testing mode:
  - 15 random asanas
  - Show image
  - 3 answer options via buttons
  - +1 for correct, +0 for incorrect
  - Show result at the end

## Tech stack
- Python
- python-telegram-bot v21+
- Supabase (Postgres) for asanas and progress
- Images stored locally and referenced by filename
- Environment variables via .env

## Architecture rules
- Do not put all logic in one file
- Use handlers/ for bot logic
- Use utils/ for helpers and database access
- Keep code minimal and readable
- No overengineering
