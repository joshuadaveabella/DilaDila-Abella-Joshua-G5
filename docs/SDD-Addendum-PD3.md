# SDD Addendum (PD3) – Resolution of ISS-03

During PD2 the implemented database differed from the SDD in three places. In PD3 the **code is the reference** and the SDD is amended as follows.

| # | SDD said | Implemented (and kept) | Why |
|---|----------|------------------------|-----|
| 1 | `phrases` had no activation flag | `phrases.is_active BOOLEAN DEFAULT TRUE` | BR-15: a phrase that students saved is deactivated, not deleted. |
| 2 | `phrasebook_entries.phrase_id` ON DELETE SET NULL | ON DELETE **PROTECT** (restricted) | SET NULL would silently turn a student's saved library phrase into an empty entry. |
| 3 | no uniqueness on saved phrases | partial UNIQUE (`user_id`, `phrase_id`) where `phrase_id` is not null | A student saves a given library phrase only once. |

Additional PD3 constraints (all enforced in PostgreSQL, not only in forms):
`categories_name_not_blank`, `phrases_cebuano_not_blank`, `phrases_english_not_blank`, `phrasebook_custom_text_not_blank`.

Foreign-key delete rules: `phrases.category_id` PROTECT; `phrasebook_entries.user_id` CASCADE (BR-07); `phrasebook_entries.phrase_id` PROTECT.
