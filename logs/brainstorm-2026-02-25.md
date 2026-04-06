# Brainstorm: FERPA-compliant anonymization for LLM workflows

**Date:** 2026-02-25

## Starting question

Is dauber capable as-is to obfuscate user/student names to make data
passed through an LLM FERPA compliant? If not, what would it take to
add a flag to commands that deal with importing and exporting student
submissions?

## Key ideas explored

- Easel currently embeds `user_name` and `user_email` verbatim in
  assessment JSON and grading output — no anonymization exists
- Structured-field stripping (blanking `user_name`/`user_email`) is
  sufficient; submission text scanning is out of scope
- Simple strip preferred over reversible mapping — `user_id` (numeric
  Canvas ID) is enough for grade submission round-trip
- Opt-in `--anonymize` flag on all submission-related commands, not
  default-on
- Stripping belongs in the service layer (consistent with existing
  data-shaping patterns like HTML stripping)

## Open questions

- Flag name: `--anonymize` vs `--redact` (leaning `--anonymize`)
- Whether `user_id` alone is considered PII under specific
  institutional FERPA interpretations (likely not — opaque integer)

## Next steps

- Plan and implement `--anonymize` flag across grading and assessment
  commands, with service-layer stripping
