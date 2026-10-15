# 06 — Background jobs

> Status: skeleton

## Facts (measured)
- `app/features/jobs/job_handlers.py`: **5,495 lines**, every handler in one file.

## To write
- One handler module per feature, registered with `@register_handler`
- Payload schema per job type
